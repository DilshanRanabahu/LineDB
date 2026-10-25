"use strict";

// ---------- building SQL text (no page access, so Node can test these) ----------

const NAME_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;

/** A value as SQL: 42 stays 42, Kamal becomes 'Kamal', O'Brien 'O''Brien'. */
function sqlLiteral(value, type) {
  if (type === "INT") {
    const text = String(value).trim();
    if (!/^-?\d+$/.test(text)) {
      throw new Error(`"${value}" is not a whole number`);
    }
    return text;
  }
  return "'" + String(value).replace(/'/g, "''") + "'";
}

function keyCondition(column, value) {
  return `${column.name} = ${sqlLiteral(value, column.type)}`;
}

function selectAllSql(table) {
  return `SELECT * FROM ${table};`;
}

function insertSql(table, columns, values) {
  const literals = columns.map((c, i) => sqlLiteral(values[i], c.type));
  return `INSERT INTO ${table} VALUES (${literals.join(", ")});`;
}

function updateSql(table, columns, values, key, keyValue) {
  const sets = columns.map((c, i) => `${c.name} = ${sqlLiteral(values[i], c.type)}`);
  return `UPDATE ${table} SET ${sets.join(", ")} WHERE ${keyCondition(key, keyValue)};`;
}

function deleteSql(table, key, keyValue) {
  return `DELETE FROM ${table} WHERE ${keyCondition(key, keyValue)};`;
}

function createTableSql(name, columns) {
  const nameRule = "use letters, digits and _, and do not start with a digit";
  if (!NAME_RE.test(name)) {
    throw new Error(`Table name "${name}": ${nameRule}`);
  }
  if (columns.length === 0) {
    throw new Error("Add at least one column");
  }
  for (const c of columns) {
    if (!NAME_RE.test(c.name)) {
      throw new Error(`Column name "${c.name}": ${nameRule}`);
    }
  }
  const list = columns.map((c) => `${c.name} ${c.type}`).join(", ");
  return `CREATE TABLE ${name} (${list});`;
}

function dropTableSql(table) {
  return `DROP TABLE ${table};`;
}

// ---------- talking to the server ----------

async function runSql(sql) {
  try {
    const response = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql }),
    });
    return await response.json();
  } catch (err) {
    return { results: [], error: "Could not reach the LineDB server. Is it still running?" };
  }
}

const state = {
  tables: [],         // [{name, columns: [{name, type}]}]
  types: ["INT", "TEXT"],
  current: null,      // name of the table being browsed, or null
};

async function refreshTables() {
  try {
    const response = await fetch("/api/tables");
    const data = await response.json();
    state.tables = data.tables;
    state.types = data.types;
  } catch (err) {
    // keep the old list; runSql reports connection problems to the user
  }
  renderTableList();
}

// ---------- drawing the page ----------

const $ = (id) => document.getElementById(id);

/** Create an element. Children that are strings become text, never HTML. */
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  for (const child of children) {
    if (child !== null && child !== undefined) node.append(child);
  }
  return node;
}

function renderTableList() {
  $("table-list").replaceChildren(...state.tables.map((t) =>
    el("li", {},
      el("button", {
        class: "table-link" + (t.name === state.current ? " active" : ""),
        onclick: () => browse(t.name),
      },
        el("span", {}, t.name),
        el("span", { class: "muted" }, `${t.columns.length} col`)))));
  $("no-tables").hidden = state.tables.length > 0;
}

function resultTable(columns, rows, rowActions) {
  const extra = rowActions ? 1 : 0;
  const head = el("tr", {},
    ...columns.map((c) => el("th", {}, c)),
    rowActions ? el("th", { class: "actions" }) : null);
  const body = rows.map((row) => el("tr", {},
    ...row.map((v) => el("td", { class: typeof v === "number" ? "num" : "" }, String(v))),
    rowActions ? el("td", { class: "actions" }, ...rowActions(row)) : null));
  if (rows.length === 0) {
    body.push(el("tr", {},
      el("td", { class: "empty", colspan: String(columns.length + extra) }, "No rows")));
  }
  return el("div", { class: "table-wrap" },
    el("table", {}, el("thead", {}, head), el("tbody", {}, ...body)));
}

/** A green or red box saying what just happened, with the SQL that ran. */
function noticeBox(notice) {
  return el("div", { class: "notice " + (notice.error ? "error" : "ok") },
    el("strong", {}, notice.error ? `Error: ${notice.message}` : notice.message),
    notice.sql ? el("code", {}, notice.sql) : null);
}

function noticeFrom(reply, sql) {
  if (reply.error) return { error: true, message: reply.error, sql };
  return { message: reply.results.map((r) => r.message).join(", "), sql };
}

/** Show the results of statements typed into the editor. */
function showResults(reply) {
  state.current = null;
  renderTableList();
  const blocks = reply.results.map((r) =>
    el("div", { class: "result" },
      el("code", { class: "result-sql" }, r.sql),
      r.columns ? resultTable(r.columns, r.rows) : null,
      el("p", { class: "result-message" }, r.message)));
  if (reply.error) blocks.push(noticeBox({ error: true, message: reply.error }));
  $("output").replaceChildren(...blocks);
}

/** Show every row of one table, with buttons to change it. */
async function browse(name, notice) {
  const sql = selectAllSql(name);
  $("sql").value = sql;
  const reply = await runSql(sql);
  await refreshTables();
  const table = state.tables.find((t) => t.name === name);
  if (reply.error || !table) {
    showResults(reply);
    return;
  }
  state.current = name;
  renderTableList();

  const result = reply.results[0];
  const key = table.columns[0];
  $("output").replaceChildren(el("div", { class: "view" },
    el("div", { class: "view-head" },
      el("div", {},
        el("h2", {}, name),
        el("code", { class: "schema" },
          table.columns.map((c) => `${c.name} ${c.type}`).join(", "))),
      el("div", { class: "buttons" },
        el("button", { class: "btn primary", onclick: () => openRowDialog(table) }, "+ Add row"),
        el("button", { class: "btn danger", onclick: () => dropTable(name) }, "Drop table"))),
    notice ? noticeBox(notice) : null,
    resultTable(result.columns, result.rows, (row) => [
      el("button", { class: "btn small", onclick: () => openRowDialog(table, row) }, "Edit"),
      el("button", { class: "btn small danger", onclick: () => deleteRow(table, row) }, "Delete"),
    ]),
    el("p", { class: "footnote" },
      `${result.message}. Edit and Delete find rows by the first column (${key.name}).`)));
}

// ---------- actions ----------

async function runEditor() {
  const sql = $("sql").value;
  if (!sql.trim()) return;
  $("run").disabled = true;
  const reply = await runSql(sql);
  $("run").disabled = false;
  await refreshTables();
  showResults(reply);
}

async function deleteRow(table, row) {
  const key = table.columns[0];
  const sql = deleteSql(table.name, key, row[0]);
  if (!confirm(`Delete every row where ${key.name} = ${row[0]}?\n\n${sql}`)) return;
  const reply = await runSql(sql);
  browse(table.name, noticeFrom(reply, sql));
}

async function dropTable(name) {
  const sql = dropTableSql(name);
  if (!confirm(`Drop table "${name}" and all of its rows? This cannot be undone.\n\n${sql}`)) {
    return;
  }
  const reply = await runSql(sql);
  await refreshTables();
  showResults(reply);
}

function showError(id, message) {
  $(id).textContent = message;
  $(id).hidden = false;
}

// ---------- add / edit row dialog ----------

let rowDialog = null;     // {table, row}: row is null when adding

function openRowDialog(table, row = null) {
  rowDialog = { table, row };
  const key = table.columns[0];
  $("row-title").textContent = row ? `Edit row in ${table.name}` : `Add row to ${table.name}`;
  $("row-fields").replaceChildren(...table.columns.map((c, i) =>
    el("label", { class: "field" },
      el("span", {}, c.name, " ", el("small", { class: "muted" }, c.type)),
      el("input", {
        autocomplete: "off",
        inputmode: c.type === "INT" ? "numeric" : "text",
        value: row ? String(row[i]) : "",
      }))));
  $("row-note").textContent = row ? `Saving changes every row where ${key.name} = ${row[0]}.` : "";
  $("row-error").hidden = true;
  $("row-dialog").showModal();
  $("row-fields").querySelector("input").focus();
}

async function saveRow(event) {
  event.preventDefault();
  const { table, row } = rowDialog;
  const values = [...$("row-fields").querySelectorAll("input")].map((input) => input.value);
  let sql;
  try {
    sql = row
      ? updateSql(table.name, table.columns, values, table.columns[0], row[0])
      : insertSql(table.name, table.columns, values);
  } catch (err) {
    showError("row-error", err.message);
    return;
  }
  const reply = await runSql(sql);
  if (reply.error) {
    showError("row-error", reply.error);
    return;
  }
  $("row-dialog").close();
  browse(table.name, noticeFrom(reply, sql));
}

// ---------- new table dialog ----------

function addColumnRow(name = "", type = "INT") {
  const row = el("div", { class: "column-row" },
    el("input", { class: "col-name", autocomplete: "off", placeholder: "column name", value: name }),
    el("select", { class: "col-type", "aria-label": "type" },
      ...state.types.map((t) => {
        const option = el("option", { value: t }, t);
        option.selected = t === type;
        return option;
      })),
    el("button", {
      type: "button", class: "btn small danger", "aria-label": "remove column",
      onclick: () => row.remove(),
    }, "×"));
  $("column-rows").append(row);
  return row;
}

function openTableDialog() {
  $("new-table-name").value = "";
  $("column-rows").replaceChildren();
  addColumnRow("id", "INT");
  addColumnRow("name", "TEXT");
  $("table-error").hidden = true;
  $("table-dialog").showModal();
  $("new-table-name").focus();
}

async function saveTable(event) {
  event.preventDefault();
  const name = $("new-table-name").value.trim();
  const columns = [...$("column-rows").querySelectorAll(".column-row")].map((r) => ({
    name: r.querySelector(".col-name").value.trim(),
    type: r.querySelector(".col-type").value,
  }));
  let sql;
  try {
    sql = createTableSql(name, columns);
  } catch (err) {
    showError("table-error", err.message);
    return;
  }
  const reply = await runSql(sql);
  if (reply.error) {
    showError("table-error", reply.error);
    return;
  }
  $("table-dialog").close();
  browse(name, noticeFrom(reply, sql));
}

// ---------- start ----------

function start() {
  $("run").addEventListener("click", runEditor);
  $("sql").addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      runEditor();
    }
  });
  $("new-table").addEventListener("click", openTableDialog);
  $("add-column").addEventListener("click", () => addColumnRow().querySelector("input").focus());
  $("row-form").addEventListener("submit", saveRow);
  $("table-form").addEventListener("submit", saveTable);
  for (const button of document.querySelectorAll("[data-close]")) {
    button.addEventListener("click", () => button.closest("dialog").close());
  }
  refreshTables();
}

if (typeof module !== "undefined") {
  // loaded by Node for the tests
  module.exports = {
    sqlLiteral, selectAllSql, insertSql, updateSql, deleteSql, createTableSql, dropTableSql,
  };
} else {
  start();
}
