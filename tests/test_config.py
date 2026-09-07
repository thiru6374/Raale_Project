from src.config.settings import Settings

def test_configuration_loads_correctly():
    settings = Settings()
    assert settings.temperature_weight == 0.4
    assert settings.number_of_teams == 5
    assert settings.maximum_travel_time == 60
