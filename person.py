import json

class Person:

    @staticmethod # This is a static method, so it does not need an instance of the class to be called
    def load_person_data():
        """A Function that knows where the person database is and returns a dictionary with the persons"""
        file = open("data/person_db.json")
        person_data = json.load(file)
        return person_data

    @staticmethod
    def get_person_list(person_data):
        """A function that returns a list of persons"""
        #person_data = load_person_data()
        person_list = []
        for person in person_data:
            person_list.append(person["lastname"] + " " + person["firstname"])
        return person_list

    @staticmethod
    def find_person_data_by_name(name_search):
        """A function that returns the data of a person by their name"""
        person_data = Person.load_person_data()
        for person in person_data:
            if person["lastname"] + " " + person["firstname"] == name_search:
                return person
        # If no person is found, return None
        return None
    
    
    def _init_(self, person_dict):
        """Initialize a Person object with a dictionary of person data"""
        self.dat_of_birth = person_dict["date_of_birth"]
        self.firstname = person_dict["firstname"]
        self.lastname = person_dict["lastname"]
        self.picture_path = person_dict["picture_path"]
        self.id = person_dict["id"]
        self.ekg_tests = person_dict["ekg_tests"] # Do we need this?


if __name__ == "__main__":
    # Test the function
    #person_data = load_person_data()
    #print(person_data)
    #person_list = get_person_list()
    #print(person_list)

    persons = Person.load_person_data()
    person_names = Person.get_person_list(persons)
    print(person_names)
    print(Person.find_person_data_by_name("Huber Julian"))