
def check_single_edge_odd_compliance_simulated(odd: dict, metadata: dict) -> bool:
    # boolean flags logic - FIXED VERSION
    oneway_odd = odd.get('oneway', True)
    if isinstance(oneway_odd, list) and len(oneway_odd) > 0:
        oneway_odd = oneway_odd[0]
    
    if not oneway_odd and not metadata.get('oneway'):
        return False

    major_road_odd = odd.get('is_major_road', True)
    if isinstance(major_road_odd, list) and len(major_road_odd) > 0:
        major_road_odd = major_road_odd[0]

    if not major_road_odd and not metadata.get('is_major_road'):
        return False
        
    return True

def test_boolean_logic():
    print("Testing boolean logic with list inputs (FIXED LOGIC)...")
    
    # Case 1: odd['oneway'] is [False]
    # metadata['oneway'] is False
    # Expected: 
    # oneway_odd becomes False.
    # "not oneway_odd" is True.
    # "not metadata.get('oneway')" is True.
    # Result should be False (Incompliant).
    
    odd_param = {'oneway': [False]}
    metadata = {'oneway': False}
    
    result = check_single_edge_odd_compliance_simulated(odd_param, metadata)
    print(f"odd={{'oneway': [False]}}, metadata={{'oneway': False}} -> Result: {result}")
    
    if result is False:
        print("SUCCESS: [False] was correctly interpreted as False, leading to incompliance.")
    else:
        print("FAILURE: Still returning True.")

if __name__ == "__main__":
    test_boolean_logic()
