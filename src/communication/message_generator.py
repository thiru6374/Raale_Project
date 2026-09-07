import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("message_generator")

class MessageGenerator:
    """Generates localised public health advisories based on specific risk factors."""

    def generate_messages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Appends a 'localised_advisory' column to the dataframe for selected neighbourhoods.
        """
        logger.info("Generating localized communication messages...")
        result_df = df.copy()
        messages = []

        for _, row in result_df.iterrows():
            if not row.get('selected_for_outreach', False):
                messages.append(None)
                continue

            name = row.get('neighbourhood_name', 'your area')
            category = row.get('multi_factor_risk_category', 'UNKNOWN')
            
            # Base Tone
            if category == 'EXTREME':
                msg = f"URGENT ALERT for {name}: Extreme heat conditions detected. "
            else:
                msg = f"Health Advisory for {name}: High heat risks today. "

            # Rule 1: Green Cover
            green_cover = row.get('green_cover_percent')
            if pd.notna(green_cover) and green_cover < 0.15:
                msg += "Due to low tree canopy, avoid outdoor surfaces which will retain extreme heat. Seek air-conditioned indoor cooling centers. "
            else:
                msg += "Stay in shaded areas if you must be outside. "

            # Rule 2: Elderly Population
            elderly = row.get('elderly_population_percent')
            if pd.notna(elderly) and elderly > 0.15:
                msg += "Please check on elderly neighbours and relatives who are highly vulnerable today. "

            # Rule 3: Healthcare Access
            distance = row.get('healthcare_distance_km')
            if pd.notna(distance) and distance > 3.0:
                msg += "Medical facilities are far from your location. Stay hydrated and call for emergency transit immediately at the first sign of heat stroke."
            else:
                msg += "Stay hydrated and seek local medical help if you experience nausea or dizziness."

            messages.append(msg.strip())

        result_df['localised_advisory'] = messages
        return result_df
