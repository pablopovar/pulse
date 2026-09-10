from pathlib import Path
APP=Path(__file__).resolve().parents[1]
def test_no_flask_daemon_workflows():
    offenders={}
    for rel in ('app.py','crawlers/seo.py'):
        hits=[i for i,line in enumerate((APP/rel).read_text().splitlines(),1) if 'threading.Thread(' in line or 'daemon=True' in line]
        if hits: offenders[rel]=hits
    assert offenders=={}
