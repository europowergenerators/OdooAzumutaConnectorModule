from enum import Enum
from typing import TypedDict, List, Tuple
import requests

from odoo import _, models
from odoo.exceptions import ValidationError
import logging
from datetime import datetime, timedelta, timezone
import re

_logger = logging.getLogger(__name__)

API_BASE_URL = "https://azumutaodoosyncwebapp-fudrctfqf7aadwds.westeurope-01.azurewebsites.net/"

class AzumutaEmployee(TypedDict):
    firstName: str
    lastName: str
    email: str
    language: str
    jobTitle: str


class AzumutaStatuscodes(Enum):
    OK = 200
    BAD_REQUEST = 400
    API_KEY_EXPIRED = 401
    SERVICE_DOWN = 500

class ApiEndpoints(Enum):
    SWAGGER = "swagger/index.html"

    LOGIN = "Api/v1/Auth/Login"
    REFRESH_TOKEN = "Api/v1/Auth/RefreshToken"
    LOGOUT = "Api/v1/Auth/Logout"
    REGISTER = "Api/v1/Auth/Register"

    SYNC_EMPLOYEE = "Api/v1/Employees/SyncEmployee"
    SYNC_EMPLOYEE_LIST = "Api/v1/Employees/SyncEmployeesList"
    GET_EMPLOYEES_LIST = "Api/v1/Employees/GetEmployeesList"

class ErrorMessages(Enum):
    INVALID_DATA = _("There is an issue with the data of one of the employees. Please fix.")
    API_UNAVAILABLE = _("The Azumuta API appears to be down. Please try again later.")
    INVALID_NAME = _("An employee has an invalid employee name.")
    NO_JOB = _("An employee has no job attached to him.")
    EMAIL_GENERATION_FAILED = _(
        "Due to a missing work email, Odoo tried generating an email "
        "based on first/last name for Azumuta but failed to do so. "
    )
    MISSING_API_TOKEN = _(
        "API tokens for the Azumuta sync is not configured. Check out: "
        + API_BASE_URL + ApiEndpoints.SWAGGER.value
        + " And add these values in the system parameters"
    )
    UNKNOWN_ERROR = _("An unknown error has occured, please check the system logs.")


class HrEmployee(models.AbstractModel):
    _inherit = "hr.employee.base"

    def action_sync_to_azumuta(self):
        # Button under the actions menu on an employee
        employees_list: List[AzumutaEmployee] = _create_azumuta_employee_dictionary(self)
        _sync_to_azumuta(self.env, employees_list)
    

    def make_azumuta_retrieve_employees_api_call(self) -> str:
        _refresh_api_jwt_token(self.env)
        headers = {
            "Authorization": "Bearer " + _retrieve_api_jwt_token(self.env),
            "Content-Type": "application/json"
        }
        print(headers)
        response = requests.get(API_BASE_URL + ApiEndpoints.GET_EMPLOYEES_LIST.value, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(response.text)
            raise ValidationError(ErrorMessages.UNKNOWN_ERROR)


def _sync_to_azumuta(env, employees_list: List[AzumutaEmployee]):
    if _is_jwt_expired(env):
        print("expired")
        _refresh_api_jwt_token(env)

    status_code, response = _make_azumuta_sync_employee_api_call(env, employees_list)
    _handle_azumuta_status_code(env, status_code, response, employees_list)

def _is_jwt_expired(env):
    expiration_str = _retrieve_api_jwt_expiration(env)

    # Normalize ISO 8601 string to allow up to 6 fractional digits
    normalized_str = re.sub(r'(\.\d{6})\d+', r'\1', expiration_str)

    # Convert expiration string to a datetime object
    expiration_datetime = datetime.fromisoformat(normalized_str)
    
    # Ensure the datetime is timezone-aware
    if expiration_datetime.tzinfo is None:
        expiration_datetime = expiration_datetime.replace(tzinfo=timezone.utc)
    
    # Current time in UTC
    current_time = datetime.now(timezone.utc)
    
    # Check if the token has expired or will expire in the next minute
    if expiration_datetime <= current_time + timedelta(minutes=1):
        return True
    
    return False
    

def _handle_azumuta_status_code(env, status_code, response, employees_list):
    if status_code == AzumutaStatuscodes.OK.value:
        env.user.notify_success(message="Successfully synced the user(s)")
        return

    elif status_code == AzumutaStatuscodes.BAD_REQUEST.value:
        print(response)
        raise ValidationError(ErrorMessages.INVALID_DATA.value)

    elif status_code == AzumutaStatuscodes.API_KEY_EXPIRED.value:
        _refresh_api_jwt_token(env)
        return _sync_to_azumuta(env, employees_list)

    elif status_code == AzumutaStatuscodes.SERVICE_DOWN.value:
        print(response)
        raise ValidationError(ErrorMessages.API_UNAVAILABLE.value)

    else:
        print(status_code)
        print(response)
        raise ValidationError(ErrorMessages.UNKNOWN_ERROR.value)

def _refresh_api_jwt_token(env):
    jwt_token, refresh_token = _retrieve_api_jwt_and_refresh_token(env)
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "jwtToken": jwt_token,
        "refreshToken": refresh_token
    }
    print(API_BASE_URL + ApiEndpoints.REFRESH_TOKEN.value)
    print(headers)
    print(payload)
    response = requests.post(API_BASE_URL + ApiEndpoints.REFRESH_TOKEN.value, headers=headers, json=payload)
    if response.status_code != 200:
        print(response.status_code)
        print(response.text)
        raise ValidationError(ErrorMessages.UNKNOWN_ERROR.value)
    
    data = response.json()

    env['ir.config_parameter'].sudo().set_param('azumuta.api.jwt_token', data["token"])
    env['ir.config_parameter'].sudo().set_param('azumuta.api.jwt_expiration', data["expiration"])
    env['ir.config_parameter'].sudo().set_param('azumuta.api.refresh_token', data["refreshToken"])
    env.cr.commit()


def _retrieve_api_jwt_and_refresh_token(env) -> Tuple[str, str]:
    jwt_token = _retrieve_api_jwt_token(env)
    refresh_token = _retrieve_api_refresh_token(env)
    return (jwt_token, refresh_token)

def _make_azumuta_sync_employee_api_call(env, employees_list: List[AzumutaEmployee]) -> Tuple[int, str]:
    headers = {
        "Authorization": "Bearer " + _retrieve_api_jwt_token(env),
        "Content-Type": "application/json"
    }
    payload = {
        "employees": employees_list
    }
    response = requests.post(API_BASE_URL + ApiEndpoints.SYNC_EMPLOYEE_LIST.value, headers=headers, json=payload)
    return response.status_code, response.text

def _retrieve_api_jwt_token(env) -> str:
    token = env['ir.config_parameter'].sudo().get_param('azumuta.api.jwt_token')
    if not token:
        raise ValidationError(ErrorMessages.MISSING_API_TOKEN)
    
    return token
    
def _retrieve_api_jwt_expiration(env) -> str:
    token = env['ir.config_parameter'].sudo().get_param('azumuta.api.jwt_expiration')
    if not token:
        raise ValidationError(ErrorMessages.MISSING_API_TOKEN)
    
    return token

def _retrieve_api_refresh_token(env) -> str:
    token = env['ir.config_parameter'].sudo().get_param('azumuta.api.refresh_token')
    if not token:
        raise ValidationError(ErrorMessages.MISSING_API_TOKEN)
    
    return token

def _create_azumuta_employee_dictionary(self) -> List[AzumutaEmployee]:
    employee_dictionary: List[AzumutaEmployee] = []
    for employee in self:
        azumuta_employee: AzumutaEmployee = _get_employee_info(employee)
        employee_dictionary.append(azumuta_employee)
    return employee_dictionary


def _get_employee_info(employee) -> AzumutaEmployee:
    email = _get_employee_email(employee)
    job_title = _get_employee_job_title(employee)
    employee_name = _get_employee_name(employee)
    azumuta_employee: AzumutaEmployee = {
        "firstName": employee_name.split()[0],
        "lastName": ''.join(employee_name.split()[1:]),
        "email": email,
        "language": "en",
        "jobTitle": job_title,
    }
    return azumuta_employee


def _get_employee_name(employee) -> str:
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


def _get_employee_job_title(employee) -> str:
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


def _get_employee_email(employee) -> str:
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
