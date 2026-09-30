from src.config.settings import Settings

def test_configuration_loads_correctly():
    settings = Settings()
    # Phase 2: Formal model updated temperature_weight to 0.3 and added mobility_weight=0.15
    assert settings.temperature_weight == 0.3
    assert settings.mobility_weight == 0.15
    assert settings.number_of_teams == 5
    assert settings.maximum_travel_time == 60
