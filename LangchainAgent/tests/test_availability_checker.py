import unittest
from unittest.mock import MagicMock, patch

# Import the module to be tested (will be implemented later)
# from src.availability_checker import AvailabilityChecker

class TestAvailabilityChecker(unittest.TestCase):
    """Test cases for the AvailabilityChecker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock Firebase client
        self.firebase_client = MagicMock()
        
        # We'll implement this class later
        # self.checker = AvailabilityChecker(firebase_client=self.firebase_client)
        
        # Sample employee data for testing
        self.sample_employees = [
            {
                "employee_number": "EMP001",
                "name": "John Doe",
                "location": "London",
                "skills": ["Frontend Developer", "React", "JavaScript"],
                "rank": {"level": 6, "official_name": "Consultant"}
            },
            {
                "employee_number": "EMP002",
                "name": "Jane Smith",
                "location": "London",
                "skills": ["Backend Developer", "Python", "Django"],
                "rank": {"level": 5, "official_name": "Senior Consultant"}
            }
        ]
        
        # Sample availability data
        self.sample_availability = {
            "results": [
                {
                    "employee_number": "EMP001",
                    "availability": [
                        {"week": 1, "status": "Available", "hours": 40},
                        {"week": 2, "status": "Not Available", "hours": 0}
                    ]
                },
                {
                    "employee_number": "EMP002",
                    "availability": [
                        {"week": 1, "status": "Partially Available", "hours": 20},
                        {"week": 2, "status": "Available", "hours": 40}
                    ]
                }
            ],
            "error": None
        }
    
    def test_availability_checker_queries_availability(self):
        """Test that the checker queries availability correctly."""
        # Mock Firebase availability response
        self.firebase_client.fetch_availability_batch.return_value = self.sample_availability
        
        # Employee data and weeks to check
        employees = self.sample_employees
        weeks = [1, 2]
        
        # We'll implement this method later
        # results = self.checker.check(employees, weeks)
        
        # Verify that Firebase client was called correctly
        # self.firebase_client.fetch_availability_batch.assert_called_once()
        # call_args = self.firebase_client.fetch_availability_batch.call_args
        # employee_ids = call_args[0][1]  # Second argument should be employee IDs
        # self.assertEqual(len(employee_ids), 2)
        # self.assertIn("EMP001", employee_ids)
        # self.assertIn("EMP002", employee_ids)
        # self.assertEqual(call_args[0][2], weeks)  # Third argument should be weeks
        
        # Verify results
        # self.assertEqual(len(results), 2)
        # self.assertEqual(results[0]["name"], "John Doe")
        # self.assertEqual(results[0]["availability"][0]["week"], 1)
        # self.assertEqual(results[0]["availability"][0]["status"], "Available")
        # self.assertEqual(results[0]["availability"][1]["week"], 2)
        # self.assertEqual(results[0]["availability"][1]["status"], "Not Available")
        
        # self.assertEqual(results[1]["name"], "Jane Smith")
        # self.assertEqual(results[1]["availability"][0]["week"], 1)
        # self.assertEqual(results[1]["availability"][0]["status"], "Partially Available")
        # self.assertEqual(results[1]["availability"][1]["week"], 2)
        # self.assertEqual(results[1]["availability"][1]["status"], "Available")
    
    def test_availability_checker_reuses_employee_results(self):
        """Test that the checker reuses employee results for follow-up queries."""
        # Mock Firebase availability response
        self.firebase_client.fetch_availability_batch.return_value = {
            "results": [
                {
                    "employee_number": "EMP001",
                    "availability": [
                        {"week": 3, "status": "Available", "hours": 40}
                    ]
                },
                {
                    "employee_number": "EMP002",
                    "availability": [
                        {"week": 3, "status": "Not Available", "hours": 0}
                    ]
                }
            ],
            "error": None
        }
        
        # Employee data with existing availability data
        employees_with_availability = [
            {
                "employee_number": "EMP001",
                "name": "John Doe",
                "location": "London",
                "skills": ["Frontend Developer", "React", "JavaScript"],
                "rank": {"level": 6, "official_name": "Consultant"},
                "availability": [
                    {"week": 1, "status": "Available", "hours": 40},
                    {"week": 2, "status": "Not Available", "hours": 0}
                ]
            },
            {
                "employee_number": "EMP002",
                "name": "Jane Smith",
                "location": "London",
                "skills": ["Backend Developer", "Python", "Django"],
                "rank": {"level": 5, "official_name": "Senior Consultant"},
                "availability": [
                    {"week": 1, "status": "Partially Available", "hours": 20},
                    {"week": 2, "status": "Available", "hours": 40}
                ]
            }
        ]
        
        # New week to check
        weeks = [3]
        
        # We'll implement this method later
        # results = self.checker.check(employees_with_availability, weeks)
        
        # Verify that Firebase client was called correctly
        # self.firebase_client.fetch_availability_batch.assert_called_once()
        
        # Verify results
        # self.assertEqual(len(results), 2)
        # self.assertEqual(results[0]["name"], "John Doe")
        # self.assertEqual(len(results[0]["availability"]), 3)  # Should have 3 weeks now
        # self.assertEqual(results[0]["availability"][2]["week"], 3)
        # self.assertEqual(results[0]["availability"][2]["status"], "Available")
        
        # self.assertEqual(results[1]["name"], "Jane Smith")
        # self.assertEqual(len(results[1]["availability"]), 3)  # Should have 3 weeks now
        # self.assertEqual(results[1]["availability"][2]["week"], 3)
        # self.assertEqual(results[1]["availability"][2]["status"], "Not Available")
    
    def test_availability_checker_handles_missing_data(self):
        """Test that the checker handles missing availability data gracefully."""
        # Mock Firebase availability response with missing data
        self.firebase_client.fetch_availability_batch.return_value = {
            "results": [
                {
                    "employee_number": "EMP001",
                    "availability": [
                        {"week": 1, "status": "Available", "hours": 40}
                    ]
                }
                # No data for EMP002
            ],
            "error": None
        }
        
        # Employee data
        employees = self.sample_employees
        weeks = [1]
        
        # We'll implement this method later
        # results = self.checker.check(employees, weeks)
        
        # Verify results
        # self.assertEqual(len(results), 2)
        # self.assertEqual(results[0]["name"], "John Doe")
        # self.assertEqual(results[0]["availability"][0]["week"], 1)
        # self.assertEqual(results[0]["availability"][0]["status"], "Available")
        
        # self.assertEqual(results[1]["name"], "Jane Smith")
        # self.assertEqual(len(results[1]["availability"]), 1)
        # self.assertEqual(results[1]["availability"][0]["week"], 1)
        # self.assertEqual(results[1]["availability"][0]["status"], "Unknown")  # Should default to Unknown
    
    def test_availability_checker_handles_error(self):
        """Test that the checker handles errors gracefully."""
        # Mock Firebase availability response with error
        self.firebase_client.fetch_availability_batch.return_value = {
            "results": [],
            "error": "Failed to fetch availability data"
        }
        
        # Employee data
        employees = self.sample_employees
        weeks = [1]
        
        # We'll implement this method later
        # results = self.checker.check(employees, weeks)
        
        # Verify results
        # self.assertEqual(len(results), 2)
        # self.assertEqual(results[0]["name"], "John Doe")
        # self.assertEqual(len(results[0]["availability"]), 1)
        # self.assertEqual(results[0]["availability"][0]["week"], 1)
        # self.assertEqual(results[0]["availability"][0]["status"], "Unknown")  # Should default to Unknown
        
        # self.assertEqual(results[1]["name"], "Jane Smith")
        # self.assertEqual(len(results[1]["availability"]), 1)
        # self.assertEqual(results[1]["availability"][0]["week"], 1)
        # self.assertEqual(results[1]["availability"][0]["status"], "Unknown")  # Should default to Unknown
    
    def test_availability_checker_handles_multiple_weeks(self):
        """Test that the checker handles multiple weeks correctly."""
        # Mock Firebase availability response with multiple weeks
        self.firebase_client.fetch_availability_batch.return_value = {
            "results": [
                {
                    "employee_number": "EMP001",
                    "availability": [
                        {"week": 1, "status": "Available", "hours": 40},
                        {"week": 2, "status": "Available", "hours": 40},
                        {"week": 3, "status": "Not Available", "hours": 0},
                        {"week": 4, "status": "Partially Available", "hours": 20}
                    ]
                },
                {
                    "employee_number": "EMP002",
                    "availability": [
                        {"week": 1, "status": "Not Available", "hours": 0},
                        {"week": 2, "status": "Not Available", "hours": 0},
                        {"week": 3, "status": "Available", "hours": 40},
                        {"week": 4, "status": "Available", "hours": 40}
                    ]
                }
            ],
            "error": None
        }
        
        # Employee data
        employees = self.sample_employees
        weeks = [1, 2, 3, 4]
        
        # We'll implement this method later
        # results = self.checker.check(employees, weeks)
        
        # Verify results
        # self.assertEqual(len(results), 2)
        # self.assertEqual(results[0]["name"], "John Doe")
        # self.assertEqual(len(results[0]["availability"]), 4)
        
        # self.assertEqual(results[1]["name"], "Jane Smith")
        # self.assertEqual(len(results[1]["availability"]), 4)
        
        # Check specific weeks
        # self.assertEqual(results[0]["availability"][0]["week"], 1)
        # self.assertEqual(results[0]["availability"][0]["status"], "Available")
        # self.assertEqual(results[0]["availability"][3]["week"], 4)
        # self.assertEqual(results[0]["availability"][3]["status"], "Partially Available")
        
        # self.assertEqual(results[1]["availability"][0]["week"], 1)
        # self.assertEqual(results[1]["availability"][0]["status"], "Not Available")
        # self.assertEqual(results[1]["availability"][3]["week"], 4)
        # self.assertEqual(results[1]["availability"][3]["status"], "Available")

if __name__ == '__main__':
    unittest.main() 