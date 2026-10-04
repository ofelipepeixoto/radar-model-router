const assert = require('node:assert/strict');
const fs = require('node:fs');
const cp = require('node:child_process');
const os = require('node:os');
const path = require('node:path');
const w = JSON.parse(fs.readFileSync('integrations/n8n/router-input.workflow.json','utf8'));
assert.equal(w.active,false);
assert.deepEqual(w.nodes.map(n=>n.type),['n8n-nodes-base.manualTrigger','n8n-nodes-base.code']);
const output = new Function(w.nodes[1].parameters.jsCode)()[0].json;
assert.equal(output.execution,'not_connected');
const state = fs.mkdtempSync(path.join(os.tmpdir(),'radar-router-'));
try {
  const python = process.env.PYTHON || 'python3';
  const result = cp.spawnSync(python,['-m','radar_router.cli','--state-dir',state],{input:JSON.stringify(output.route_input),encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
  assert.equal(JSON.parse(result.stdout).tier,1);
  console.log('n8n code -> Python CLI contract: PASS (not real n8n execution)');
} finally { fs.rmSync(state,{recursive:true,force:true}); }
