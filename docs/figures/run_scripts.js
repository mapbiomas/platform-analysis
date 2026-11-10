/**
 * Runs the GEE scripts in codes/ on single example pixels, outside Earth Engine.
 *
 * Each script is executed top to bottom, unchanged, inside a Node `vm` sandbox where `ee`,
 * `Map` and `require` are replaced by a minimal one-pixel implementation: an ee.Image is a list
 * of bands, each holding one value or null (masked). Every Map.addLayer call is captured and the
 * value of the layer's first band is reported, so the method figure shows what the scripts
 * actually compute.
 *
 * Usage:  node run_scripts.js pixels.json   (pixels.json: {"A": {"1985": 3, ...}, ...})
 * Output: JSON on stdout: {script: {pixel: {layerName: value | null}}}
 *
 * Only the operations the scripts use are implemented; anything else throws, so a script that
 * starts using a new operation fails loudly here instead of producing a wrong figure.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const CODES = path.resolve(__dirname, '..', '..', 'codes');
const ASSET = 'projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_coverage_v1';

// --- server-side value wrappers (evaluated eagerly) -------------------------------------------

const val = (x) => (x && x.__v !== undefined ? val(x.__v) : Array.isArray(x) ? x.map(val) : x);

function EeNumber(n) {
    return {
        __v: val(n),
        format(fmt) {
            if (fmt !== '%.0f') throw new Error('format not mocked: ' + fmt);
            return EeString(String(Math.round(this.__v)));
        },
    };
}

function EeString(s) {
    return { __v: String(val(s)), cat(o) { return EeString(this.__v + String(val(o))); } };
}

function EeList(arr) {
    const items = val(arr);
    return {
        __v: items,
        map(fn) { return EeList(items.map((x) => fn(x))); },
        iterate(fn, first) { return items.reduce((acc, x) => fn(x, acc), first); },
        reverse() { return EeList(items.slice().reverse()); },
        get(i) { return items[val(i)]; },
    };
}

// --- one-pixel image ---------------------------------------------------------------------------

class Img {
    constructor(bands) { this.bands = bands; } // [{name, v}] with v === null for masked

    static of(x, pixel) {
        if (x instanceof Img) return x;
        if (typeof x === 'string') {
            if (x !== ASSET) throw new Error('unexpected asset: ' + x);
            return new Img(Object.keys(pixel).map((y) => ({ name: 'classification_' + y, v: pixel[y] })));
        }
        if (Array.isArray(x)) return new Img([].concat(...x.map((i) => Img.of(i, pixel).bands)));
        if (typeof val(x) === 'number') return new Img([{ name: 'constant', v: val(x) }]);
        throw new Error('ee.Image() argument not mocked');
    }

    _other(o) {
        if (o instanceof Img) return o;
        return new Img([{ name: 'constant', v: val(o) }]);
    }

    // band-wise binary op; a one-band operand is broadcast; names come from the left operand
    _bin(o, fn) {
        const b = this._other(o).bands;
        if (b.length !== 1 && b.length !== this.bands.length) throw new Error('band count mismatch');
        return new Img(this.bands.map((band, i) => {
            const ob = b.length === 1 ? b[0] : b[i];
            return { name: band.name, v: band.v === null || ob.v === null ? null : fn(band.v, ob.v) };
        }));
    }

    eq(o) { return this._bin(o, (a, b) => (a === b ? 1 : 0)); }
    add(o) { return this._bin(o, (a, b) => a + b); }
    subtract(o) { return this._bin(o, (a, b) => a - b); }
    multiply(o) { return this._bin(o, (a, b) => a * b); }

    select(sel) {
        const names = [].concat(val(sel));
        return new Img(names.map((n) => {
            const band = this.bands.find((b) => b.name === n);
            if (!band) throw new Error('band not found: ' + n);
            return { ...band };
        }));
    }

    bandNames() { return EeList(this.bands.map((b) => b.name)); }
    rename(n) { return new Img(this.bands.map((b, i) => ({ name: [].concat(val(n))[i], v: b.v }))); }
    unmask(v) { return new Img(this.bands.map((b) => ({ name: b.name, v: b.v === null ? v : b.v }))); }
    selfMask() { return new Img(this.bands.map((b) => ({ name: b.name, v: b.v ? b.v : null }))); }
    toInt16() { return this; }

    // a zero or masked mask value masks the pixel
    mask(m) { return this._bin(m, (a, k) => (k ? a : null)); }

    remap(from, to) {
        return new Img(this.bands.map((b) => {
            const i = from.indexOf(b.v);
            return { name: b.name, v: b.v === null || i < 0 ? null : to[i] };
        }));
    }

    reduce(r) {
        const vals = this.bands.map((b) => b.v).filter((v) => v !== null);
        return new Img([{ name: r.name, v: r.fn(vals) }]);
    }
}

const Reducer = {
    sum: () => ({ name: 'sum', fn: (v) => (v.length ? v.reduce((a, b) => a + b, 0) : null) }),
    max: () => ({ name: 'max', fn: (v) => (v.length ? Math.max(...v) : null) }),
    countDistinctNonNull: () => ({ name: 'count', fn: (v) => new Set(v).size }),
    countRuns: () => ({ name: 'count', fn: (v) => v.filter((x, i) => i === 0 || x !== v[i - 1]).length }),
    firstNonNull: () => ({ name: 'first', fn: (v) => (v.length ? v[0] : null) }),
};

// --- run --------------------------------------------------------------------------------------

function runScript(file, pixel) {
    const layers = {};
    const ee = {
        Image: (x) => Img.of(x, pixel),
        Number: EeNumber,
        String: EeString,
        List: EeList,
        Reducer,
    };
    const sandbox = {
        ee,
        Map: { addLayer: (img, vis, name) => { layers[name] = img.bands[0].v; } },
        require: () => ({ get: () => [] }),
        print: () => {},
    };
    vm.runInNewContext(fs.readFileSync(path.join(CODES, file), 'utf8'), sandbox, { filename: file });
    return layers;
}

const pixels = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const scripts = fs.readdirSync(CODES).filter((f) => /^analysis_\d+_.*\.js$/.test(f)).sort();
const out = {};
for (const s of scripts) {
    out[s] = {};
    for (const [name, px] of Object.entries(pixels)) out[s][name] = runScript(s, px);
}
process.stdout.write(JSON.stringify(out));
