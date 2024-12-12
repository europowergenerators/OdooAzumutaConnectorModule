from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from ..models.hr_employee import ErrorMessages

@tagged("post_install", "-at_install", "europowergenerators")
class TestAzumutaEmployeeSync(TransactionCase):
    def setUp(self):
        super().setUp()
        # Setting up a demo employee
        self.product_template_1 = self.env["product.template"].create(
            {
                "name": "Test Product",
            }
        )

    def test_successfull_action_on_one_employee(self):
        pass

    def test_employee_with_middle_name(self):
        pass

    def test_successfull_action_on_multiple_employees(self):
        pass

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

    def test_successfull_sync_and_validate_on_azumuta(self):
        pass
