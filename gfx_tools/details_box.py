import re
import json
from colorama import Fore, Back
if __name__ == '__main__': #handle for different places the script is called from
    from watch_attributes import get_watch_attributes, get_watch_number
    #from get_alert_geometry import get_alert_geometry
else:
    from gfx_tools.watch_attributes import get_watch_attributes, get_watch_number
    #from gfx_tools.get_alert_geometry import get_alert_geometry

def get_hazard_details(alert, geom_type):
    """Using Regex, gets hazard details for the hazard lines box for a given alert, as well as callouts from the JSON

    Args:
        alert (NWS Alert Object): Alert to get info from
        geom_type (str): 'zone' or 'county'

    Returns:
        hazard_details (tuple with value, label, and suffix): List of values to be processed into the text box.
        torSeverity  Parameter from alert JSON.
        tStormSeverity (str):  Parameter from alert JSON
        floodSeverity (str): Parameter from alert JSON
        torDetection (str): Parameter from alert JSON
        waterspoutDetection (str): Parameter from alert JSON
    """    
    try:
        print(Fore.LIGHTBLUE_EX + "Scanning alert text for attributes." + Fore.RESET)
        alert_type = alert['properties'].get("event")
        #geom, geom_type = get_alert_geometry(alert)
        
        
        maxWind = alert['properties']['parameters'].get('maxWindGust', ["n/a"])[0] #integer
        maxHail = alert['properties']['parameters'].get('maxHailSize', ["n/a"])[0] #float
        windObserved = alert['properties']['parameters'].get('windThreat', ["n/a"])[0]
        hailObserved = alert['properties']['parameters'].get('hailThreat', ["n/a"])[0]
        torDetection = alert['properties']['parameters'].get('tornadoDetection', ['n/a'])[0] #string, possible for svr; radar-indicated, radar-confirmed, need to see others for tor warning
        floodSeverity = alert['properties']['parameters'].get('flashFloodDamageThreat', ['n/a'])[0] #string, default level (unsure what this returns), considerable, catastophic
        tStormSeverity = alert['properties']['parameters'].get('thunderstormDamageThreat', ['n/a'])[0] 
        torSeverity = alert['properties']['parameters'].get('tornadoDamageThreat', ['n/a'])[0] #considerable for pds, catastrophic for tor e
        floodDetection = alert['properties']['parameters'].get('flashFloodDetection', ['n/a'])[0]
        snowSquallDetection = alert['properties']['parameters'].get('snowSquallDetection', ['n/a'])[0] #"RADAR INDICATED" or "OBSERVED"
        snowSquallImpact = alert['properties']['parameters'].get('snowSquallImpact', ['n/a'])[0] # "SIGNIFICANT" or nothing
        waterspoutDetection = alert['properties']['parameters'].get('waterspoutDetection', ['n/a'])[0] #"OBSERVED" or "POSSIBLE"
        #sps stuff
        fireWeatherThreat = 'n/a'
        denseFogThreat = 'n/a'
        iceThreat = 'n/a'
        additionalHazard = 'n/a' 
        #watch stuff (add the word and percentage)
        torProb = 'n/a'
        sigTorProb = 'n/a'
        windProb = 'n/a'
        sigWindProb = 'n/a'
        hailProb = 'n/a'
        sigHailProb = 'n/a'
        #flood stuff
        rainFallen = 'n/a'
        additionalRain = 'n/a'
        #high wind warnings
        hwwWind = 'n/a'
        hwwGust = 'n/a'

        #watch getting
        watch_attribs, watch_percents = ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a'], ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a']  #default to these
        if alert_type == 'Severe Thunderstorm Watch' or alert_type == 'Tornado Watch':
            description_text = alert['properties'].get('description', '').lower()
            watch_id = get_watch_number(description_text)
            
            if watch_id != None:
                _, watch_attribs, watch_percents = get_watch_attributes(watch_id)
                torProb = watch_attribs[0] + ' - ' + watch_percents[0]
                sigTorProb = watch_attribs[1] + ' - ' + watch_percents[1]
                windProb = watch_attribs[2] + ' - ' + watch_percents[2]
                sigWindProb = watch_attribs[3] + ' - ' + watch_percents[3]
                hailProb = watch_attribs[4] + ' - ' + watch_percents[4]
                sigHailProb = watch_attribs[5] + ' - ' + watch_percents[5]
            else:
                print('error getting watch id from watch text!')
                watch_attribs, watch_percents = ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a'], ['n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a']

        #handling SMWs because they don't have maxwind/maxhail in their parameters
        if alert_type == 'Special Marine Warning':
            description_text = alert['properties'].get('description','').lower()
            if maxWind == 'n/a':
                wind_match = re.search(r"wind gusts.*?(\d+)\s*knots", description_text) #regex is beyond me
                if wind_match:
                    maxWind = f"{wind_match.group(1)}kts"
            
            if maxHail == 'n/a':
                hail_match = re.search(r"hail.*?([\d.]+)\s*inch", description_text)
                if hail_match:
                    try:
                        #convert to float
                        maxHail = float(hail_match.group(1))
                    except ValueError:
                        print('could not parse hail size from description')
                        
        #handle flood related things, so rain amts and mudslides
        if alert_type in ['Flash Flood Warning', 'Flood Advisory']:
            # Normalize the text: collapse newlines/tabs/multiple spaces into single spaces
            raw_desc = alert['properties'].get('description', '')
            description_text = ' '.join(raw_desc.split()).lower()
            #print(description_text)

            # --- Rain that has already fallen ---
            fallen_pattern = (
                r"(?i)"
                r"(?:"
                    r"between\s+([\d.]+)\s*(?:and|to|-)\s*([\d.]+)"  # between X and Y
                    r"|([\d.]+)\s*to\s*([\d.]+)"                     # X to Y
                    r"|up\s*to\s*([\d.]+)"                           # up to X
                    r"|([\d.]+)"                                     # single value
                r")"
                r"\s*inch(?:es)?(?:\s+of\s+rain)?"
                r"(?:[^.]{0,80})?"                                  # allow filler before "have fallen"
                r"\b(?:have|has)\s+fallen"                                  # anchor
            )

            # --- Additional rain expected / possible ---
            additional_pattern = (
                r"(?i)"
                r"additional\s+rainfall\s+amounts\s+(?:of\s+)?"
                r"(?:"
                    r"up\s*to\s*([\d.]+)"                            # up to X
                    r"|([\d.]+)\s*(?:to|and|-)\s*([\d.]+)"           # X to Y
                    r"|([\d.]+)"                                     # single value
                r")"
                r"\s*inch(?:es)?(?:[^.]{0,60})?(?:\s+(?:are|is|remain|will\s+be|could\s+be)\s+\w+)?"  # filler
            )
            
            mudslide_pattern = (
                r"(mudslide)|(a mudslide)"
            )

            fallen_match = re.search(fallen_pattern, description_text)
            additional_match = re.search(additional_pattern, description_text)
            mudslide_match = re.search(mudslide_pattern, description_text)

            rainFallen = 'n/a'
            additionalRain = 'n/a'
            additionalHazard = 'n/a'

            if fallen_match:
                g = fallen_match.groups()
                # groups: (between1, between2, to1, to2, up_to, single)
                if g[0] and g[1]:
                    rainFallen = f"{g[0]} - {g[1]}"
                elif g[2] and g[3]:
                    rainFallen = f"{g[2]} - {g[3]}"
                elif g[4]:
                    rainFallen = f"up to {g[4]}"
                elif g[5]:
                    rainFallen = g[5]

            if additional_match:
                g = additional_match.groups()
                # groups: (up_to, between1, between2, single)
                if g[1] and g[2]:
                    additionalRain = f"{g[1]} - {g[2]}"
                elif g[0]:
                    additionalRain = f"up to {g[0]}"
                elif g[3]:
                    additionalRain = g[3]
            
            if mudslide_match:
                g = mudslide_match.groups()
                #print(mudslide_match.groups())
                additionalHazard = 'Mudslide'


            #print("Accumulated Rainfall:", rainFallen)
        # print("Additional rain:", additionalRain)

        #handle non-convective SPS                
        if alert_type == 'Special Weather Statement' and geom_type == 'zone':
            #print('regexing SPS for more infos')
            specific_hazard_found = False
            description_text = alert['properties'].get('description', '').lower()
            headline_text = alert['properties']['parameters'].get('NWSheadline', [''])[0]
            search_text = description_text + ' ' + headline_text

            # Define regex patterns, need to flesh these out some more
            fire_regex = r'\bfire\b|\bwildfire\b|red\s*flag'
            fog_regex = r'dense\s*fog|visibility\s*(?:one|a)\s*quarter\s*mile|zero\s*visibility|\bareas\s+of\s+fog\b'
            ice_regex = r'\bice\b|\bicy\b'
            blackice_regex =  r'black\s+ice'
            funnel_regex = r'funnel\s+cloud' #search sps for funnel clouds possible
            sps_gusty_winds_regex = r'strong\s+winds'

            # Search for matches, ignoring case
            if re.search(fire_regex, search_text, re.IGNORECASE):
                fireWeatherThreat = "Elevated"
                specific_hazard_found = True
            if re.search(fog_regex, search_text, re.IGNORECASE):
                denseFogThreat = "Likely"
                specific_hazard_found = True

            if re.search(ice_regex, search_text, re.IGNORECASE):
                iceThreat = "Possible Across the Area"
                specific_hazard_found = True
            if re.search(blackice_regex, search_text, re.IGNORECASE):
                iceThreat = 'Black Ice Possible'
                specific_hazard_found = True
            if re.search(funnel_regex, search_text, re.IGNORECASE):
                additionalHazard = 'Funnel Clouds Possible'
                specific_hazard_found = True
            if re.search(sps_gusty_winds_regex, search_text, re.IGNORECASE):
                additionalHazard = 'Gusty (non Tstorm) Winds Possible'
                specific_hazard_found = True
            
            if not specific_hazard_found:
                if headline_text:
                    additionalHazard = headline_text
                else:
                    additionalHazard = 'See Statement for Details'
                

        if alert_type == 'Dense Fog Advisory':
            denseFogThreat = 'Likely'
        
        if alert_type == 'High Wind Warning':
            raw_desc = alert['properties'].get('description', '')
            description_text = ' '.join(raw_desc.split()).lower()
            
            wind_pattern = r"\b(?:[Nn]orth|[Ss]outh|[Ee]ast|[Ww]est)?\s*winds?\s+(?:around\s+)?(\d+(?:\s*(?:to|-)\s*\d+)?)\s*mph"
            gust_pattern = r"\bgusts?\s+(?:up to|around)?\s*(\d+(?:\s*(?:to|-)\s*\d+)?)\s*mph"

            wind_match = re.search(wind_pattern, description_text)
            gust_match = re.search(gust_pattern, description_text)

            hwwWind = wind_match.group(1) if wind_match else 'n/a'
            hwwGust = gust_match.group(1) if gust_match else 'n/a'
            
        if alert_type == 'Red Flag Warning':
            fireWeatherThreat = 'Very High'
        
        hazard_details = [
            ('Max. Wind Gusts', maxWind, ''),
            ('Max. Hail Size', maxHail, 'in'),
            ('Damage Threat', floodSeverity, ''),
            ('Damage Threat', tStormSeverity, ''),
            ('Damage Threat', torSeverity, ''),
            ('Impact', snowSquallImpact, ''),
            ('Tornado', torDetection, ''),
            ('Waterspout', waterspoutDetection, ''),
            ('Snow Squall', snowSquallDetection, ''),
            ('Flash Flood', floodDetection, ''),
            ('Risk of Fire Weather', fireWeatherThreat, ''),
            ('Fog Development', denseFogThreat, ''),
            ('Icy Conditions', iceThreat, ''),
            ('Tornado Probability', torProb, ''),
            ('Sig. Tornado Probability', sigTorProb, ''),
            ('Wind Probability', windProb, ''),
            ('Sig. Wind Probability', sigWindProb, ''),
            ('Hail Probability', hailProb, ''),
            ('Sig. Hail Probability', sigHailProb, ''),
            ('Accumulated Rainfall', rainFallen, 'in'),
            ('Additional Rain', additionalRain, 'in'),
            ('Hazard', additionalHazard, ''),
            ('Max. Sustained Wind', hwwWind, ' MPH'), #seperate ones from the normal winds 
            ('Max. Wind Gusts', hwwGust, ' MPH')
        ]
        
        
        details_text_lines = []
        for label, value, suffix in hazard_details:
            if value != "n/a" and value != 'n/a - n/a' and value != '0.00': #second one is for the watch probs if there aren't any #third is for hail
                # Escape any spaces in the value for LaTeX rendering
                escaped_value = str(value).replace(" ", r"\ ")
                
                # Start the LaTeX string with the bolded value and its unit/suffix
                # Example: $\bf{1.25in}
                formatted_string = f"$\\bf{{{escaped_value}{suffix}}}"
                
                # Check if the 'OBSERVED' tag is needed for this specific hazard
                is_observed = False
                if label == 'Max. Wind Gusts' and windObserved == 'OBSERVED':
                    is_observed = True
                elif label == 'Max. Hail Size' and hailObserved == 'OBSERVED':
                    is_observed = True
                
                if is_observed:
                    # If observed, add a space and the italicized tag
                    # Example: \ \mathit{(OBSERVED)}
                    formatted_string += r"\ \mathit{(observed)}"

                # Close the LaTeX math string
                formatted_string += "$"
                
                details_text_lines.append(f"{label}: {formatted_string}")
        print(Fore.LIGHTBLUE_EX + "Successfully scanned alert text for attributes." + Fore.RESET)
        return details_text_lines, torSeverity, tStormSeverity, floodSeverity, torDetection, waterspoutDetection
    except Exception as e:
        print(Back.RED + f"Error using Regex to get details_text!! {e}" + Back.RESET)
        return None, None, None, None, None, None

if __name__ == '__main__':
    with open('test_alerts/ffw_regex_test.json', 'r') as file: 
        test_alert = json.load(file) 
    get_hazard_details(test_alert)