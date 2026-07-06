def test_app_database_loaded():
    import app

    coverage = app.db.coverage()
    assert coverage['n_materials'] >= 300
    assert coverage['n_property_rows'] >= 3000
    assert app.DRUG_NAMES
    assert app.COMPONENT_NAMES
