/* API client – all fetch calls go through here */
const API = (() => {
  const base = window.location.origin;

  async function request(method, path, body, timeoutMs = 8000) {
    const isForm = body instanceof FormData;
    const opts   = { method, headers: isForm ? {} : { 'Content-Type': 'application/json' } };
    if (body) opts.body = isForm ? body : JSON.stringify(body);

    // Abort controller for timeout
    const ctrl = new AbortController();
    opts.signal = ctrl.signal;
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);

    let res;
    try {
      res = await fetch(base + path, opts);
    } catch (err) {
      if (err.name === 'AbortError') throw new Error(`Request timed out (${timeoutMs / 1000}s)`);
      throw err;
    } finally {
      clearTimeout(timer);
    }

    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try { const j = await res.json(); msg = j.detail || j.message || msg; } catch {}
      throw new Error(msg);
    }
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) return res.json();
    return res;
  }

  return {
    get:    (path)        => request('GET',    path),
    post:   (path, body)  => request('POST',   path, body),
    put:    (path, body)  => request('PUT',    path, body),
    patch:  (path, body)  => request('PATCH',  path, body),
    delete: (path)        => request('DELETE', path),
  };
})();
