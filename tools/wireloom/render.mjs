// Render a Wireloom source to SVG.  Usage: node render.mjs <in.wireloom> <out.svg> [theme]
// One-time setup in this dir:  npm install wireloom
// Rasterize to PNG for quick viewing:  rsvg-convert -o out.png out.svg
import { readFileSync, writeFileSync } from 'node:fs';
import wireloom from 'wireloom';
const [src, out, theme = 'dark'] = process.argv.slice(2);
const { svg } = await wireloom.render('mock', readFileSync(src, 'utf8'), { theme });
writeFileSync(out, svg);
console.log('wrote', out, svg.length, 'bytes');
