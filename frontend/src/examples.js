// Ejemplos precargados para cada modo de entrada.
const mk = (id, type, x, y, data = {}) => ({ id, type, position: { x, y }, data })
const ed = (source, target, sign = '+', sh, th) => ({ id: `${source}-${target}-${sh || ''}${th || ''}`, source, target, sourceHandle: sh, targetHandle: th, data: { sign } })

export const BLOCK_EXAMPLES = {
  'Realimentación unitaria': {
    nodes: [mk('r', 'input', 0, 80), mk('e', 'sum', 110, 70), mk('g', 'block', 220, 60, { name: 'G', tf: 'K/(s*(s+2))' }),
      mk('b', 'branch', 430, 87), mk('y', 'output', 520, 80)],
    edges: [ed('r', 'e', '+', undefined, 'l'), ed('e', 'g'), ed('g', 'b'), ed('b', 'y'), ed('b', 'e', '-', 'b', 'b')],
    params: { K: 4 },
  },
  'Realimentación con H(s)': {
    nodes: [mk('r', 'input', 0, 80), mk('e', 'sum', 110, 70), mk('g', 'block', 220, 60, { name: 'G', tf: '10/(s*(s+2))' }),
      mk('b', 'branch', 430, 87), mk('y', 'output', 520, 80), mk('h', 'block', 250, 190, { name: 'H', tf: '1/(0.5*s+1)', flip: true })],
    edges: [ed('r', 'e', '+', undefined, 'l'), ed('e', 'g'), ed('g', 'b'), ed('b', 'y'), ed('b', 'h', '+', 'b'), ed('h', 'e', '-', undefined, 'b')],
    params: {},
  },
  'Lazos anidados (Mason)': {
    nodes: [mk('r', 'input', 0, 80), mk('e1', 'sum', 100, 70), mk('g1', 'block', 200, 60, { name: 'G_1', tf: '1/(s+1)' }),
      mk('e2', 'sum', 340, 70), mk('g2', 'block', 440, 60, { name: 'G_2', tf: '2/(s+3)' }), mk('b2', 'branch', 620, 87),
      mk('g3', 'block', 650, 60, { name: 'G_3', tf: '1/s' }), mk('b1', 'branch', 800, 87), mk('y', 'output', 880, 80),
      mk('h1', 'block', 470, 190, { name: 'H_1', tf: '0.5', flip: true }), mk('h2', 'block', 460, 290, { name: 'H_2', tf: '1', flip: true })],
    edges: [ed('r', 'e1', '+', undefined, 'l'), ed('e1', 'g1'), ed('g1', 'e2', '+', undefined, 'l'), ed('e2', 'g2'), ed('g2', 'b2'),
      ed('b2', 'g3'), ed('g3', 'b1'), ed('b1', 'y'), ed('b2', 'h1', '+', 'b'), ed('h1', 'e2', '-', undefined, 'b'),
      ed('b1', 'h2', '+', 'b'), ed('h2', 'e1', '-', undefined, 'b')],
    params: {},
  },
  'Sin realimentación (serie + paralelo)': {
    nodes: [mk('r', 'input', 0, 100), mk('b0', 'branch', 90, 107), mk('g1', 'block', 150, 30, { name: 'G_1', tf: '1/(s+1)' }),
      mk('g2', 'block', 150, 170, { name: 'G_2', tf: '2/(s+4)' }), mk('e', 'sum', 330, 100), mk('y', 'output', 420, 100)],
    edges: [ed('r', 'b0'), ed('b0', 'g1'), ed('b0', 'g2', '+', 'b'), ed('g1', 'e', '+', undefined, 't'), ed('g2', 'e', '+', undefined, 'b'), ed('e', 'y')],
    params: {},
  },
}

const part = (id, type, x, y, name, value, extra = {}) => ({ id, type: 'part', position: { x, y }, data: { ptype: type, name, value, ...extra } })
const wire = (s, sh, t, th) => ({ id: `${s}.${sh}-${t}.${th}`, source: s, sourceHandle: sh, target: t, targetHandle: th })

export const PHYS_EXAMPLES = {
  trans: {
    'Masa-resorte-amortiguador': {
      parts: [part('f', 'force', 0, 80, 'F'), part('m', 'mass', 170, 70, 'M', 2), part('k', 'spring', 340, 20, 'K', 8), part('b', 'damper', 340, 140, 'B', 3), part('w', 'ground', 520, 80, 'Pared')],
      wires: [wire('f', 'a', 'm', 'a2'), wire('m', 'a3', 'k', 'a'), wire('m', 'a3', 'b', 'a'), wire('k', 'b', 'w', 'a'), wire('b', 'b', 'w', 'a')],
      input: 'f', output: { comp: 'm', kind: 'across' },
    },
    'Dos masas acopladas': {
      parts: [part('f', 'force', 0, 90, 'F'), part('m1', 'mass', 150, 80, 'M1', 1), part('kc', 'spring', 300, 30, 'Kc', 4), part('m2', 'mass', 450, 80, 'M2', 2),
        part('k2', 'spring', 600, 30, 'K2', 6), part('b2', 'damper', 600, 150, 'B2', 2), part('w', 'ground', 760, 90, 'Pared'),
        part('b1', 'damper', 150, 200, 'B1', 1), part('w0', 'ground', 150, 290, 'Suelo')],
      wires: [wire('f', 'a', 'm1', 'a2'), wire('m1', 'a3', 'kc', 'a'), wire('kc', 'b', 'm2', 'a2'), wire('m2', 'a3', 'k2', 'a'), wire('m2', 'a3', 'b2', 'a'),
        wire('k2', 'b', 'w', 'a'), wire('b2', 'b', 'w', 'a'), wire('m1', 'a4', 'b1', 'a'), wire('b1', 'b', 'w0', 'a')],
      input: 'f', output: { comp: 'm2', kind: 'across' },
    },
  },
  rot: {
    'Inercia con fricción y resorte torsional': {
      parts: [part('t', 'torque', 0, 80, 'T'), part('j', 'inertia', 170, 70, 'J', 0.5), part('k', 'tspring', 340, 20, 'K', 4), part('b', 'rdamper', 340, 140, 'B', 0.8), part('w', 'ground', 520, 80, 'Fijo')],
      wires: [wire('t', 'a', 'j', 'a2'), wire('j', 'a3', 'k', 'a'), wire('j', 'a3', 'b', 'a'), wire('k', 'b', 'w', 'a'), wire('b', 'b', 'w', 'a')],
      input: 't', output: { comp: 'j', kind: 'across' },
    },
  },
  elec: {
    'RLC serie (tensión en C)': {
      parts: [part('v', 'vsource', 0, 80, 'V'), part('r', 'resistor', 160, 20, 'R', 1), part('l', 'inductor', 320, 20, 'L', 0.5), part('c', 'capacitor', 480, 80, 'C', 0.2), part('g', 'ground', 240, 200, 'GND')],
      wires: [wire('v', 'a', 'r', 'a'), wire('r', 'b', 'l', 'a'), wire('l', 'b', 'c', 'a'), wire('c', 'b', 'g', 'a'), wire('v', 'b', 'g', 'a')],
      input: 'v', output: { comp: 'c', kind: 'across' },
    },
    'Filtro RC paso bajo': {
      parts: [part('v', 'vsource', 0, 80, 'V'), part('r', 'resistor', 160, 20, 'R', 1000), part('c', 'capacitor', 340, 80, 'C', 0.001), part('g', 'ground', 200, 200, 'GND')],
      wires: [wire('v', 'a', 'r', 'a'), wire('r', 'b', 'c', 'a'), wire('c', 'b', 'g', 'a'), wire('v', 'b', 'g', 'a')],
      input: 'v', output: { comp: 'c', kind: 'across' },
    },
  },
}

export const MOTOR_DEFAULTS = { Ra: 1.0, La: 0.5, Kt: 0.01, Kb: 0.01, J: 0.01, B: 0.1 }
export const TF_EXAMPLES = {
  '2º orden (ωn=5, ζ=0.5)': { Gn: '25', Gd: 's*(s+5)', Hn: '1', Hd: '1', fb: 'unity' },
  'Tipo 1 con ganancia K': { Gn: 'K', Gd: 's*(s+1)*(s+2)', Hn: '1', Hd: '1', fb: 'unity', params: { K: 1.5 } },
  'Planta con cero': { Gn: '10*(s+3)', Gd: 's^2+4*s+20', Hn: '1', Hd: '1', fb: 'none' },
  'Realimentación con H': { Gn: '20', Gd: '(s+1)*(s+4)', Hn: '1', Hd: '0.2*s+1', fb: 'custom' },
  'Inestable (Routh)': { Gn: '1', Gd: 's^3+s^2+2*s+8', Hn: '1', Hd: '1', fb: 'none' },
}
