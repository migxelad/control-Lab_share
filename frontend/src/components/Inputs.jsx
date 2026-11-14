import { TF_EXAMPLES } from '../examples.js'

export function FeedbackPicker({ fb, setFb }) {
  const opt = (v, l) => (
    <label className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-sm ${fb.type === v ? 'border-sky-500 bg-sky-500/10' : 'border-slate-300 dark:border-slate-700'}`}>
      <input type="radio" name="fb" checked={fb.type === v} onChange={() => setFb({ ...fb, type: v })} />{l}
    </label>
  )
  return (
    <div className="card space-y-2 p-3">
      <span className="label">Lazo de control</span>
      <div className="flex flex-wrap gap-2">
        {opt('none', 'Lazo abierto (analizar G)')}{opt('unity', 'Realimentación unitaria')}{opt('custom', 'Realimentación H(s)')}
      </div>
      {fb.type === 'custom' && (
        <div><span className="label">H(s)</span>
          <input className="input font-mono" value={fb.H || ''} onChange={(e) => setFb({ ...fb, H: e.target.value })} placeholder="1/(0.2*s+1)" /></div>
      )}
    </div>
  )
}

export function TfEditor({ tf, setTf, loadExample }) {
  const set = (k) => (e) => setTf({ ...tf, [k]: e.target.value })
  return (
    <div className="card space-y-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">Función de transferencia de la planta G(s)</h3>
        <select className="input !w-auto" value="" onChange={(e) => loadExample(e.target.value)}>
          <option value="">Cargar ejemplo…</option>{Object.keys(TF_EXAMPLES).map((k) => <option key={k}>{k}</option>)}
        </select>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <div><span className="label">Numerador</span><input className="input font-mono" value={tf.Gn} onChange={set('Gn')} placeholder="K*(s+3)" /></div>
        <div><span className="label">Denominador</span><input className="input font-mono" value={tf.Gd} onChange={set('Gd')} placeholder="s*(s+1)*(s+2)" /></div>
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Usa <code>s</code> como variable, <code>*</code>, <code>/</code>, <code>^</code> y paréntesis. Cualquier otro símbolo (K, a, tau…) se convierte automáticamente en un
        parámetro con su propio deslizador en el panel lateral.
      </p>
    </div>
  )
}

export function MotorEditor({ motor, setMotor }) {
  return (
    <div className="card space-y-3 p-4">
      <h3 className="font-semibold">Servomotor DC (control por armadura)</h3>
      <svg viewBox="0 0 520 150" className="w-full max-w-xl text-slate-700 dark:text-slate-200" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M20 40 H70 M70 40 l8 -10 l10 20 l10 -20 l10 20 l10 -20 l8 10 H150 M150 40 c0 -14 14 -14 14 0 c0 -14 14 -14 14 0 c0 -14 14 -14 14 0 c0 -14 14 -14 14 0 H230 M230 40 H260" />
        <circle cx="20" cy="75" r="0" /><path d="M20 40 V110 H260 V80" /><circle cx="300" cy="75" r="40" /><path d="M260 40 V70" />
        <path d="M340 75 H400 M400 45 V105 M420 45 V105 M420 75 H470" strokeWidth="2.5" />
        <text x="285" y="80" fill="currentColor" stroke="none" fontSize="22">M</text>
        <text x="95" y="22" fill="currentColor" stroke="none" fontSize="13">Ra</text><text x="170" y="22" fill="currentColor" stroke="none" fontSize="13">La</text>
        <text x="2" y="80" fill="currentColor" stroke="none" fontSize="13">V</text><text x="352" y="62" fill="currentColor" stroke="none" fontSize="13">B</text>
        <text x="270" y="135" fill="currentColor" stroke="none" fontSize="12">Kt·i = J·ω' + B·ω ;  e = Kb·ω</text>
      </svg>
      <div className="grid gap-3 sm:grid-cols-3">
        <div><span className="label">Salida</span>
          <select className="input" value={motor.output} onChange={(e) => setMotor({ ...motor, output: e.target.value })}>
            <option value="speed">Velocidad ω(s)/V(s)</option><option value="position">Posición θ(s)/V(s)</option><option value="current">Corriente I(s)/V(s)</option>
          </select></div>
      </div>
      <p className="text-xs text-slate-500 dark:text-slate-400">Ajusta Ra, La, Kt, Kb, J y B con los deslizadores del panel lateral. Modelo: V = Ra·i + La·di/dt + Kb·ω ; Kt·i = J·dω/dt + B·ω.</p>
    </div>
  )
}
