"""
Person module for EKG analysis system.
Handles person data loading and retrieval operations with performance optimization.
"""

import json
from typing import Dict, List, Optional
from functools import lru_cache


class Person:
    """
    Person class for managing individual person data and providing
    static methods for database operations.
    """
    
    def __init__(self, person_dict: Dict):
        """
        Initialize a Person object with a dictionary of person data.
        
        Args:
            person_dict (Dict): Dictionary containing person data with keys:
                - date_of_birth: Birth year of the person
                - firstname: First name
                - lastname: Last name  
                - picture_path: Path to person's picture
                - id: Unique person identifier
                - ekg_tests: List of EKG test data (optional)
        """
        self.date_of_birth = person_dict["date_of_birth"]
        self.firstname = person_dict["firstname"]
        self.lastname = person_dict["lastname"] 
        self.picture_path = person_dict["picture_path"]
        self.id = person_dict["id"]
        self.ekg_tests = person_dict.get("ekg_tests", [])
    
    @property
    def full_name(self) -> str:
        """
        Get full name in 'Lastname Firstname' format.
        
        Returns:
            str: Formatted full name
        """
        return f"{self.lastname} {self.firstname}"
    
    @staticmethod
    @lru_cache(maxsize=1)
    def load_person_data() -> List[Dict]:
        """
        Load person database from JSON file with caching for performance.
        Uses LRU cache to avoid repeated file I/O operations.
        
        Returns:
            List[Dict]: List of person dictionaries containing personal and EKG data
            
        Raises:
            FileNotFoundError: If person database file doesn't exist
            json.JSONDecodeError: If JSON file is malformed
        """
        try:
            with open("data/person_db.json", "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError("Person database file not found at data/person_db.json")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON format in person database: {str(e)}")

    @staticmethod
    def get_person_list(person_data: List[Dict]) -> List[str]:
        """
        Extract list of person names in 'Lastname Firstname' format.
        Optimized with list comprehension for better performance.
        
        Args:
            person_data (List[Dict]): List of person dictionaries
            
        Returns:
            List[str]: Formatted person names
        """
        return [f"{person['lastname']} {person['firstname']}" for person in person_data]

    @staticmethod
    def find_person_data_by_name(name_search: str) -> Optional[Dict]:
        """
        Find person data by full name with optimized search.
        
        Args:
            name_search (str): Name in format 'Lastname Firstname'
            
        Returns:
            Optional[Dict]: Person data dictionary or None if not found
        """
        person_data = Person.load_person_data()
        
        # Use generator expression for memory efficiency
        for person in person_data:
            if f"{person['lastname']} {person['firstname']}" == name_search:
                return person
        
        return None
    
    @staticmethod
    def get_available_ekg_count(person_dict: Dict) -> int:
        """
        Get count of available EKG tests for a person.
        
        Args:
            person_dict (Dict): Person data dictionary
            
        Returns:
            int: Number of available EKG tests
        """
        return len(person_dict.get("ekg_tests", []))


if __name__ == "__main__":
    """
    Test module functionality when run directly.
    """
    try:
        # Test person data loading
        print("Testing Person class functionality...")
        
        persons = Person.load_person_data()
        print(f"✅ Loaded {len(persons)} persons from database")
        
        # Test person list generation
        person_names = Person.get_person_list(persons)
        print(f"✅ Generated {len(person_names)} person names")
        print(f"First few names: {person_names[:3]}")
        
        # Test person search
        if person_names:
            test_name = person_names[0]
            found_person = Person.find_person_data_by_name(test_name)
            if found_person:
                print(f"✅ Successfully found person: {test_name}")
                print(f"   EKG tests available: {Person.get_available_ekg_count(found_person)}")
            else:
                print(f"❌ Could not find person: {test_name}")
        
        print("✅ All tests completed successfully")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")