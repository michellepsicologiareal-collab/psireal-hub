from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"


def test_root_opens_the_complete_finpilot_app():
    main_source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")

    assert 'RedirectResponse(url="/static/app.html"' in main_source
    assert (STATIC / "app.html").is_file()
    assert (STATIC / "app.css").is_file()
    assert (STATIC / "app.js").is_file()


def test_frontend_contains_real_financial_workflows():
    html = (STATIC / "app.html").read_text(encoding="utf-8")
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")

    assert 'data-page="overview"' in html
    assert 'data-page="diary"' in html
    assert 'data-page="goals"' in html
    assert 'data-page="budgets"' in html
    assert "data-calculator" in html
    assert 'data-finpilot-conscious' in html

    assert 'api("/api/categories")' in javascript
    assert '"/api/transactions"' in javascript
    assert '"/api/goals"' in javascript
    assert '"/api/budgets"' in javascript
    assert "submitTransaction" in javascript
    assert "submitGoal" in javascript
    assert "submitBudget" in javascript
    assert "calcOperator" in javascript


def test_frontend_has_mobile_and_dark_mode_styles():
    css = (STATIC / "app.css").read_text(encoding="utf-8")

    assert ':root[data-theme="dark"]' in css
    assert "@media (max-width: 680px)" in css
    assert ".bottom-nav" in css


def test_frontend_contains_full_finpilot_screens_and_forms():
    html = (STATIC / "app.html").read_text(encoding="utf-8")
    javascript = (STATIC / "app.js").read_text(encoding="utf-8")

    for label in (
        "Categorias",
        "Calendário",
        "Caixinhas de metas",
        "Planejamento",
        "Contas e patrimônio",
        "Lembretes financeiros",
        "Modo Consciente",
    ):
        assert label in html

    assert "data-account-form" in html
    assert "data-scheduled-form" in html
    assert "data-purchase-form" in html
    assert "subcategory_id" in html
    assert "/api/scheduled-expenses" in javascript
    assert "/api/purchase-plans" in javascript
