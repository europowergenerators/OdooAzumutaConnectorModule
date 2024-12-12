from enum import Enum
from typing import TypedDict

from odoo import _, models
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class AzumutaEmployee(TypedDict):
    name: str
    email: str
    job_title: str


class AzumutaStatuscodes(Enum):
    OK = 200
    BAD_REQUEST = 400
    API_KEY_EXPIRED = 401
    SERVICE_DOWN = 500

class ErrorMessages(Enum):
    INVALID_DATA = _("There is an issue with the data of one of the employees. Please fix.")
    API_UNAVAILABLE = _("The Azumuta API appears to be down. Please try again later.")
    INVALID_NAME = _("An employee has an invalid employee name.")
    NO_JOB = _("An employee has no job attached to him.")
    EMAIL_GENERATION_FAILED = _(
        "Due to a missing work email, Odoo tried generating an email "
        "based on first/last name for Azumuta but failed to do so. "
    )

class HrEmployee(models.AbstractModel):
    _inherit = "hr.employee.base"

    def action_sync_to_azumuta(self):
        # Button under the actions menu on an employee
        employees_list: list[AzumutaEmployee] = _create_azumuta_employee_dictionary(self)
        _sync_to_azumuta(employees_list)


def _sync_to_azumuta(employees_list):
    status_code = _make_azumuta_api_call(employees_list)
    _handle_azumuta_status_code(status_code, employees_list)


def _handle_azumuta_status_code(status_code, employees_list):
    if status_code == AzumutaStatuscodes.OK.value:
        # Notify user of success
        return

    elif status_code == AzumutaStatuscodes.BAD_REQUEST.value:
        raise ValidationError(ErrorMessages.INVALID_DATA.value)

    elif status_code == AzumutaStatuscodes.API_KEY_EXPIRED.value:
        # Refresh JWT token and then call the SYNC again
        return _sync_to_azumuta(employees_list)

    elif status_code == AzumutaStatuscodes.SERVICE_DOWN.value:
        raise ValidationError(ErrorMessages.API_UNAVAILABLE.value)


def _make_azumuta_api_call(employees_list):
    # Mock making the request
    return 200


def _create_azumuta_employee_dictionary(self):
    employee_dictionary: list[AzumutaEmployee] = []
    for employee in self:
        azumuta_employee: AzumutaEmployee = _get_employee_info(employee)
        employee_dictionary.append(azumuta_employee)
    return employee_dictionary


def _get_employee_info(employee):
    email = _get_employee_email(employee)
    job_title = _get_employee_job_title(employee)
    employee_name = _get_employee_name(employee)
    azumuta_employee: AzumutaEmployee = {
        "email": email,
        "job_title": job_title,
        "name": employee_name,
    }
    return azumuta_employee


def _get_employee_name(employee):
    """This function will return the employee's name

    Args:
        employee (dict): Employee dictionary from odoo

    Raises:
        ValidationError: Raised when an employee has an invalid name

    Returns:
        str: Employee name
    """
    if employee["name"]:
        return employee["name"]

    raise ValidationError(ErrorMessages.INVALID_NAME.value)


def _get_employee_job_title(employee):
    """This function will return the employee's job name

    Args:
        employee (dict): Employee dictionary from odoo

    Raises:
        ValidationError: Raised when an employee has no job title

    Returns:
        str: Job title
    """
    if employee["job_id"]:
        return employee["job_id"]["name"]

    raise ValidationError(ErrorMessages.NO_JOB.value)


def _get_employee_email(employee):
    """This function will return the employee's work email.
    If this does not exist, it will create an email based on the employee's name instead.

    Args:
        employee (dict): Employee dictionary from odoo

    Raises:
        ValidationError: Raised when an error occurs while creating the employee's fake work email

    Returns:
        str: Work email
    """
    if employee["work_email"]:
        return employee["work_email"]

    else:
        employee_name = employee["name"].split(" ")
        if len(employee_name) >= 2:
            try:
                first_name = employee_name[0]
                middle_and_last_name = "".join(name_part for name_part in employee_name[1:])
                return f"{first_name}.{middle_and_last_name}@e-powerinternational.com"
            except Exception as e:
                _logger.error(e)

        raise ValidationError(
            ErrorMessages.EMAIL_GENERATION_FAILED.value
        )
