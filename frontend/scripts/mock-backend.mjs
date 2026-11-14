import { createServer } from 'node:http';
const port = Number(process.env.PORT || 8000);
const history = [];
const schema = { database_type: 'SQLite', database_name: 'DataPilot Business Database', connected: true, tables: [{ name: 'customers', columns: [{ name: 'customer_id', type: 'INTEGER', key: 'PK' }, { name: 'name', type: 'TEXT' }, { name: 'city', type: 'TEXT' }] }, { name: 'orders', columns: [{ name: 'order_id', type: 'INTEGER', key: 'PK' }, { name: 'customer_id', type: 'INTEGER', key: 'FK' }, { name: 'total_amount', type: 'REAL' }] }], relationships: ['customers.customer_id → orders.customer_id'] };
const evaluation = { total: null, passed: null, failed: null, metrics: { semantic: null, result: null, grounding: null }, cases: [] };
const steps = [{ label: 'Understanding question', detail: 'Mapped the business question to the available schema.', state: 'complete' }, { label: 'Generating SQL', detail: 'Generated a read-only aggregate query.', state: 'complete' }, { label: 'Validating SQL', detail: 'Checked the query against the question and safety rules.', state: 'complete' }];
function responseFor(question) {
  const lower = question.toLowerCase();
  if (lower.includes('validation') || lower.includes('invalid')) return { question, generated_sql: '', validation: 'failed', execution: 'not_evaluated', columns: [], rows: [], final_answer: 'The generated SQL was rejected during validation.', verification: { semantic: 'failed', result: 'not_evaluated', grounding: 'not_evaluated' }, execution_time: 0.4, agent_steps: steps, is_demo: false };
  if (lower.includes('execution') || lower.includes('error') || lower.includes('fail')) return { question, generated_sql: 'SELECT * FROM missing_table', validation: 'passed', execution: 'failed', columns: [], rows: [], final_answer: 'The SQL was validated but could not be executed.', verification: { semantic: 'passed', result: 'failed', grounding: 'not_evaluated' }, execution_time: 3, agent_steps: steps, is_demo: false };
  if (lower.includes('empty') || lower.includes('zero rows')) return { question, generated_sql: 'SELECT name, total_amount FROM orders WHERE total_amount < 0', validation: 'passed', execution: 'passed', columns: ['name', 'total_amount'], rows: [], final_answer: 'No rows matched the requested criteria.', verification: { semantic: 'passed', result: 'passed', grounding: 'passed' }, execution_time: 3, agent_steps: steps, is_demo: false };
  return { question, generated_sql: 'SELECT c.name AS customer, SUM(o.total_amount) AS revenue FROM customers c JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.name ORDER BY revenue DESC', validation: 'passed', execution: 'passed', columns: ['customer', 'revenue'], rows: [{ customer: 'Eva', revenue: 2400 }, { customer: 'Liam', revenue: 1750 }], final_answer: 'Eva generated the highest revenue with $2,400.', verification: { semantic: 'passed', result: 'passed', grounding: 'passed' }, execution_time: 3, agent_steps: steps, is_demo: false };
}
function send(response, status = 200) { return (request, reply) => { reply.writeHead(status, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' }); reply.end(JSON.stringify(response)); }; }
const server = createServer((request, reply) => {
  if (request.method === 'OPTIONS') return send({}, 204)(request, reply);
  if (request.url === '/api/agent/status') return send({ status: 'ready', model: 'CohereLabs/tiny-aya-global', adapter: 'none (base model)' })(request, reply);
  if (request.url === '/api/database/schema') return send(schema)(request, reply);
  if (request.url === '/api/history') return send(history)(request, reply);
  if (request.url === '/api/evaluation') return send(evaluation)(request, reply);
  if (request.url === '/api/query' && request.method === 'POST') { let body = ''; request.on('data', (chunk) => { body += chunk; }); request.on('end', () => { let payload = {}; try { payload = JSON.parse(body || '{}'); } catch { return send({ detail: 'Invalid JSON' }, 400)(request, reply); } setTimeout(() => { const result = responseFor(String(payload.question || '')); history.unshift({ id: String(Date.now()), question: result.question, timestamp: 'Just now', status: result.validation === 'failed' || result.execution === 'failed' ? 'failed' : 'passed', rows: result.rows.length, duration: result.execution_time }); send(result)(request, reply); }, 3000); }); return; }
  send({ detail: 'Not found' }, 404)(request, reply);
});
server.listen(port, '127.0.0.1', () => console.log('DataPilot mock backend listening on http://127.0.0.1:' + port));
