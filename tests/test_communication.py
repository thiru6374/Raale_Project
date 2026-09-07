import pandas as pd
from src.communication.message_generator import MessageGenerator

def test_message_generation():
    # Setup test data with different extreme scenarios
    data = pd.DataFrame({
        'neighbourhood_name': ['Concrete Jungle', 'Elderly Suburb', 'Ignored Area'],
        'selected_for_outreach': [True, True, False],
        'multi_factor_risk_category': ['EXTREME', 'HIGH', 'LOW'],
        'green_cover_percent': [0.05, 0.40, 0.50],
        'elderly_population_percent': [0.05, 0.25, 0.10],
        'healthcare_distance_km': [1.0, 5.0, 1.0]
    })
    
    generator = MessageGenerator()
    result = generator.generate_messages(data)
    
    assert 'localised_advisory' in result.columns
    
    msg1 = result['localised_advisory'].iloc[0]
    msg2 = result['localised_advisory'].iloc[1]
    msg3 = result['localised_advisory'].iloc[2]
    
    # Assert row 1 (Concrete Jungle: low green, EXTREME)
    assert "URGENT ALERT for Concrete Jungle:" in msg1
    assert "avoid outdoor surfaces" in msg1 # low green cover trigger
    assert "check on elderly" not in msg1
    
    # Assert row 2 (Elderly Suburb: high elderly, high distance)
    assert "Health Advisory for Elderly Suburb:" in msg2
    assert "check on elderly neighbours" in msg2 # high elderly trigger
    assert "Medical facilities are far" in msg2 # high distance trigger
    
    # Assert row 3 (Not selected)
    assert pd.isna(msg3)
