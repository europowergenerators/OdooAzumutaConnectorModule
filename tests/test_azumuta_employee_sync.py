from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from ..models.hr_employee import ErrorMessages
import random

class TestAzumutaEmployeeSync(TransactionCase):
    # def setUp(self):
    #     super().setUp()
    #     # Setting up a demo employee
    #     self.product_template_1 = self.env["product.template"].create(
    #         {
    #             "name": "Test Product",
    #         }
    #     )

    # IMPORTANT: Azumuta does not yet have a delete endpoint, so we will need to manually delete the test users...

    def test_successfull_action_on_one_employee(self):
        job = self.env["hr.job"].create({
            "name": "test"
        })
        random_digits = str(random.randint(1000, 9999))
        employee = self.env["hr.employee"].create({
            "name": "James Smith" + random_digits,
            "work_email": "james.smith" + random_digits + "@e-powerinternational.com",
            "job_id": job.id
        })

        employee.action_sync_to_azumuta()
        employees_in_azumuta = employee.make_azumuta_retrieve_employees_api_call()
        
        self.assertTrue(
            any(employee['work_email'] == e["email"] for e in employees_in_azumuta["employees"]),
            f"Created email not found in the list of employees."
        )

    def test_employee_with_middle_name(self):
        job = self.env["hr.job"].create({
            "name": "test"
        })
        random_digits = str(random.randint(1000, 9999))
        employee = self.env["hr.employee"].create({
            "name": "James M Smith" + random_digits,
            "work_email": "james.msmith" + random_digits + "@e-powerinternational.com",
            "job_id": job.id
        })

        employee.action_sync_to_azumuta()
        employees_in_azumuta = employee.make_azumuta_retrieve_employees_api_call()
        
        self.assertTrue(
            any(employee['work_email'] == e["email"] for e in employees_in_azumuta["employees"]),
            f"Created email not found in the list of employees."
        )

    def test_successfull_action_on_multiple_employees(self):
        job = self.env["hr.job"].create({
            "name": "test"
        })
        random_digits1 = str(random.randint(1000, 9999))
        random_digits2 = str(random.randint(1000, 9999))
        name_1 = "James Smith" + random_digits1
        name_2 = "James Smith" + random_digits2
        names = [name_1, name_2]
        employee1 = self.env["hr.employee"].create({
            "name": name_1,
            "work_email": "james.smith" + random_digits1 + "@e-powerinternational.com",
            "job_id": job.id
        })
        employee2 = self.env["hr.employee"].create({
            "name": name_2,
            "work_email": "james.smith" + random_digits2 + "@e-powerinternational.com",
            "job_id": job.id
        })
        employees = self.env["hr.employee"].search([("name", "in", names)])
        # Ensure the two employees were retrieved
        self.assertEqual(len(employees), 2, "The created employees were not found in the search.")

        employees.action_sync_to_azumuta()
        # Make the API call to retrieve employees from Azumuta
        employees_in_azumuta = employees.make_azumuta_retrieve_employees_api_call()
        
        # Check that both employees exist in the Azumuta response
        self.assertIn(employee1["work_email"], [e["email"] for e in employees_in_azumuta["employees"]],
                    f"Employee {employee1.name} not found in Azumuta.")
        self.assertIn(employee2["work_email"], [e["email"] for e in employees_in_azumuta["employees"]],
                    f"Employee {employee2.name} not found in Azumuta.")
            
        

    def test_fail_on_no_last_or_first_name(self):
        self.employee = self.env["hr.employee"].create({
            "name": "test"
        })
        with self.assertRaises(ValidationError) as error:
            self.employee.action_sync_to_azumuta()
        
        self.assertEqual(
            error.exception.args[0],
            ErrorMessages.EMAIL_GENERATION_FAILED.value,
            "We are expecting an EMAIL GENERATION FAILED Exception to be thrown"
        )

    def test_missing_job_title(self):
        self.employee = self.env["hr.employee"].create({
            "name": "test employee #1"
        })

        with self.assertRaises(ValidationError) as error:
            self.employee.action_sync_to_azumuta()
        
        self.assertEqual(
            error.exception.args[0],
            ErrorMessages.NO_JOB.value,
            "We are expecting a NO JOB Error to be thrown"
        )
    
    def test_fail_no_name(self):
        self.job = self.env["hr.job"].create({
            "name": "test"
        })
        self.employee = self.env["hr.employee"].create({
            "name": "",
            "work_email": "test.test@e-powerinternational.com",
            "job_id": self.job.id
        })
        with self.assertRaises(ValidationError) as error:
            self.employee.action_sync_to_azumuta()
        
        self.assertEqual(
            error.exception.args[0],
            ErrorMessages.INVALID_NAME.value,
            "We are expecting an INVALID NAME Exception to be thrown"
        )

    def test_api_down(self):
        pass
