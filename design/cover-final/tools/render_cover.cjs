// Render the outlined SVG without relying on fonts installed on the machine.
const fs = require('node:fs');
const path = require('node:path');
const { Resvg } = require(process.env.SVG_RENDER_MODULE || '@resvg/resvg-js');
const root = path.resolve(__dirname, '../../..');
const source = path.join(root, 'design/cover-final/cover-outlined.svg');
const width = Number(process.argv[2] || 1920);
const out = process.argv[3] || path.join(root, 'output/usa-birth-cover-1920x2560.png');
const renderer = new Resvg(fs.readFileSync(source), {
  fitTo: { mode: 'width', value: width },
  font: { loadSystemFonts: false },
});
const result = renderer.render();
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, result.asPng());
console.log(JSON.stringify({file: out, width: result.width, height: result.height}));
