# app.py - Lead Gen Tool Web UI
# Run: python app.py  →  http://localhost:5000

import sys, os, json, queue, threading, time, io, csv
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, Response, request, jsonify

app = Flask(__name__)

_searches: dict = {}       # search_id → Queue
_results:  dict = {}       # search_id → list[lead]  (for CSV export)
_lock = threading.Lock()


# ── Background search thread ──────────────────────────────────────────────────

def _run_search(search_id: str, topic: str, city: str, q: queue.Queue, max_results: int = 60):
    try:
        import config
        config.MAX_RESULTS = max_results   # runtime mein override karo
        from scraper import collect_leads
        from filter  import filter_leads, has_no_website
        from tracker import get_contact_history
        from whatsapp import clean_phone
        import contextlib

        def emit(event: dict):
            try: q.put_nowait(event)
            except queue.Full: pass

        # ── Step 1: Scrape ────────────────────────────────────────────────────
        emit({"type": "step", "step": 1,
              "message": f'"{topic}" in {city} — Google Maps search shuru...'})

        leads = collect_leads(topic, city, progress_callback=emit)
        if not leads:
            emit({"type": "error", "message": "Koi business nahi mila. Topic ya city badlo."})
            return

        # ── Step 2: Filter ────────────────────────────────────────────────────
        emit({"type": "step", "step": 2,
              "message": f"{len(leads)} businesses filter ho rahi hain..."})

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            filtered = filter_leads(leads)

        # ── Step 3: Results ───────────────────────────────────────────────────
        emit({"type": "step", "step": 3, "message": "Results ready hain!"})

        all_leads_to_send = []

        def _prep(lead, previously=False, h=None):
            lead["_wa_phone"]           = clean_phone(lead.get("phone", ""))
            lead["previously_contacted"] = previously
            if previously and h:
                lead["contacted_at"]  = h.get("contacted_at", "")
                lead["contacted_via"] = h.get("contacted_via", "whatsapp")
            return lead

        # Fresh HOT / WARM
        for lead in filtered.get("hot",  []):
            all_leads_to_send.append(("HOT",  _prep(lead)))
        for lead in filtered.get("warm", []):
            all_leads_to_send.append(("WARM", _prep(lead)))

        # Already contacted — re-emit with flag so UI shows badge
        for lead in filtered.get("already_contacted", []):
            hist      = get_contact_history(lead)
            lead_type = "HOT" if has_no_website(lead) else "WARM"
            all_leads_to_send.append((lead_type, _prep(lead, True, hist)))

        for lead_type, lead in all_leads_to_send:
            emit({"type": "lead", "lead_type": lead_type, "lead": lead})

        # Cache for CSV export
        with _lock:
            _results[search_id] = [l for _, l in all_leads_to_send]

        emit({
            "type": "done",
            "summary": {
                "hot":               len(filtered.get("hot",  [])),
                "warm":              len(filtered.get("warm", [])),
                "skipped":           len(filtered.get("skipped", [])),
                "already_contacted": len(filtered.get("already_contacted", [])),
                "total":             len(leads),
            },
        })

    except Exception as exc:
        try: q.put_nowait({"type": "error", "message": str(exc)})
        except Exception: pass
    finally:
        try: q.put_nowait(None)
        except Exception: pass
        with _lock:
            _searches.pop(search_id, None)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def start_search():
    data        = request.get_json(silent=True) or {}
    topic       = (data.get("topic") or "").strip()
    city        = (data.get("city")  or "").strip()
    max_results = int(data.get("max_results") or 60)
    max_results = max(10, min(max_results, 120))   # clamp 10-120

    if not topic: return jsonify({"error": "Topic daalo!"}), 400
    if not city:  return jsonify({"error": "City daalo!"}),  400

    search_id = str(int(time.time() * 1000))
    q = queue.Queue(maxsize=2000)
    with _lock:
        _searches[search_id] = q

    threading.Thread(
        target=_run_search, args=(search_id, topic, city, q, max_results), daemon=True
    ).start()
    return jsonify({"search_id": search_id})


@app.route("/stream/<search_id>")
def stream(search_id: str):
    with _lock:
        q = _searches.get(search_id)
    if q is None:
        return Response("Not found", status=404)

    def generate():
        while True:
            try:
                event = q.get(timeout=8)   # 8s pe keepalive — port-forward drop na ho
                if event is None:
                    yield f"data: {json.dumps({'type':'end'})}\n\n"
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type':'ping'})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/find-email", methods=["POST"])
def find_email():
    """Lead ke liye email dhundho (website scrape ya search se)."""
    lead = (request.get_json(silent=True) or {}).get("lead", {})
    if not lead:
        return jsonify({"emails": []})

    from email_finder import find_email_for_lead
    try:
        emails = find_email_for_lead(lead)
        return jsonify({"emails": emails})
    except Exception as e:
        return jsonify({"emails": [], "error": str(e)})


@app.route("/send-email", methods=["POST"])
def send_one_email():
    """Ek lead ko email bhejo."""
    data  = request.get_json(silent=True) or {}
    lead  = data.get("lead", {})
    email = data.get("email", "").strip()
    if not lead or not email:
        return jsonify({"ok": False, "error": "lead ya email missing"}), 400

    from email_sender import send_email
    result = send_email(email, lead)
    return jsonify(result)


@app.route("/send-bulk-emails", methods=["POST"])
def send_bulk():
    """Multiple leads ko ek saath email bhejo."""
    data  = request.get_json(silent=True) or {}
    items = data.get("items", [])   # [{lead:{...}, email:'x@y.com'}, ...]
    if not items:
        return jsonify({"results": []})

    def _run():
        from email_sender import send_bulk_emails
        return send_bulk_emails(items)

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(_run)
        results = future.result(timeout=120)

    return jsonify({"results": results})


@app.route("/track", methods=["POST"])
def track_lead():
    """WhatsApp button click hone par lead ko contacted mark karo."""
    data   = request.get_json(silent=True) or {}
    lead   = data.get("lead", {})
    method = data.get("method", "whatsapp")
    if not lead:
        return jsonify({"error": "lead data missing"}), 400

    from tracker  import mark_as_contacted
    from whatsapp import clean_phone
    lead["phone_cleaned"] = clean_phone(lead.get("phone", ""))
    mark_as_contacted(lead, method=method)
    return jsonify({"ok": True, "name": lead.get("name", "")})


@app.route("/export/<search_id>")
def export_csv(search_id: str):
    """Leads CSV download karo."""
    with _lock:
        leads = list(_results.get(search_id, []))

    if not leads:
        return Response("No data", status=404)

    fields = ["lead_type", "name", "phone", "website", "address",
              "city", "topic", "rating", "total_reviews",
              "reason", "google_maps_url", "previously_contacted", "contacted_at"]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(leads)

    ts = time.strftime("%Y%m%d_%H%M")
    return Response(
        "\ufeff" + output.getvalue(),       # BOM for Excel UTF-8
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="leads_{ts}.csv"'},
    )


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀  Lead Gen UI: http://localhost:{port}")
    print("    Ctrl+C se band karo\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
