import json
import pytest
from unittest import mock
from django.urls import reverse
from apps.workspaces.models import NetSuiteCredentials, Configuration, LastExportDetail
from fyle_accounting_mappings.models import MappingSetting
from .fixtures import data


#  Will use paramaterize decorator of python later
@pytest.mark.django_db(databases=['default'])
def test_netsutie_fields_view(api_client, access_token):

   url = reverse('netsuite-fields', 
      kwargs={
            'workspace_id': 1
         }
      )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code == 200
   response = json.loads(response.content)

   assert len(response) == 4


@pytest.mark.django_db(databases=['default'])
def test_destination_attribute_view(api_client, access_token):

   url = reverse('destination-attributes',
      kwargs={
         'workspace_id': 1
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url, {
      'attribute_types': 'SUBSIDIARY'
   })

   assert response.status_code == 200
   response = json.loads(response.content)

   assert response[0] == data['destination_attributes'][0]


@pytest.mark.parametrize(
    "test_input, expected",
    [("EMPLOYEE", 7), ("ACCOUNT", 123), ['PROJECT', 1086]],
)
@pytest.mark.django_db(databases=['default'])
def test_destination_attribute_count_view(test_input, expected, api_client, access_token):

   url = reverse('attributes-count',
      kwargs={
         'workspace_id': 1
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url, {
      'attribute_type': test_input
   })
   assert response.status_code == 200
   response = json.loads(response.content)
   
   assert response['count'] == expected


def test_custom_segment_view(api_client, access_token):

   url = reverse('custom-segments',
      kwargs={
         'workspace_id': 2
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.get(url)
   assert response.status_code == 200

   response = json.loads(response.content)
   assert response[0]['script_id'] == 'custcol780'


def test_trigger_export_view(api_client, access_token, mocker):
   LastExportDetail.objects.create(workspace_id=1, export_mode='MANUAL', total_expense_groups_count=2, 
    successful_expense_groups_count=0, failed_expense_groups_count=0, last_exported_at='2023-07-07 11:57:53.184441+00', 
    created_at='2023-07-07 11:57:53.184441+00', updated_at='2023-07-07 11:57:53.184441+00')

   url = reverse('trigger-exports',
      kwargs={
         'workspace_id': 1
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   response = api_client.post(url)

   assert response.status_code == 200

   
def test_trigger_payment_view(api_client, access_token, add_fyle_credentials, mocker):
   mocker.patch(
        'fyle_integrations_platform_connector.apis.Reimbursements.sync',
        return_value=[],
    )
   
   mocker.patch(
        'fyle_integrations_platform_connector.apis.Reports.bulk_mark_as_paid',
        return_value=[],
    )
   mocker.patch(
      'apps.netsuite.connector.NetSuiteConnector.get_bill',
      return_value=data['get_bill_response'][1]
   )
   mocker.patch(
      'apps.netsuite.connector.NetSuiteConnector.get_expense_report',
      return_value=data['get_expense_report_response'][0]
   )
   mocker.patch(
      'apps.netsuite.connector.NetSuiteConnector.post_vendor_payment',
      return_value=data['creation_response']
   )
   mocker.patch(
      'netsuitesdk.api.expense_reports.ExpenseReports.get',
      return_value=data['get_expense_report_response'][1]
   )
   mocker.patch(
      'netsuitesdk.api.vendor_bills.VendorBills.get',
      return_value=data['get_bill_response'][0]
   )
   workspace_id = 2

   url = reverse('trigger-payments',
      kwargs={
         'workspace_id': workspace_id
      }
   )
   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))

   configuration = Configuration.objects.get(workspace_id=workspace_id)
   configuration.sync_fyle_to_netsuite_payments = True
   configuration.save()

   response = api_client.post(url)
   assert response.status_code == 200

   configuration.sync_fyle_to_netsuite_payments = False
   configuration.sync_netsuite_to_fyle_payments = True
   configuration.save()

   response = api_client.post(url)
   assert response.status_code == 200


def test_sync_netsuite_dimensions(api_client, access_token, add_netsuite_credentials):

   url = reverse('sync-dimensions',
      kwargs={
         'workspace_id': 2
      }
   )

   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   
   response = api_client.post(url)
   assert response.status_code == 200

   with mock.patch('apps.netsuite.views.Workspace.objects.get') as mock_call:
      mock_call.side_effect = Exception()

      response = api_client.post(url)
      assert response.status_code == 400
      assert response.data['message'] == 'Error in syncing Dimensions'

   netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=2)
   netsuite_credentials.delete()

   response = api_client.post(url)

   assert response.status_code == 400
   assert response.data['message'] == 'NetSuite credentials not found in workspace'


def test_refresh_netsuite_dimensions(api_client, access_token, add_netsuite_credentials):

   url = reverse('refresh-dimensions',
      kwargs={
         'workspace_id': 2
      }
   )

   MappingSetting.objects.create(
      source_field = 'PROJECT',
      destination_field='PROJECT',
      import_to_fyle = True,
      workspace_id=2,
      is_custom= False
   )

   MappingSetting.objects.create(
      source_field = 'COST_CENTER',
      destination_field='CLASS',
      import_to_fyle = True,
      workspace_id=2,
      is_custom= False
   )

   MappingSetting.objects.create(
      source_field = 'KLASS',
      destination_field='DEPARTMENT',
      import_to_fyle = False,
      workspace_id=2,
      is_custom= True
   )


   api_client.credentials(HTTP_AUTHORIZATION='Bearer {}'.format(access_token))
   
   response = api_client.post(url)
   assert response.status_code == 200

   with mock.patch('apps.netsuite.views.Workspace.objects.get') as mock_call:
      mock_call.side_effect = Exception()

      response = api_client.post(url)
      assert response.status_code == 400
      assert response.data['message'] == 'Error in refreshing Dimensions'

   netsuite_credentials = NetSuiteCredentials.get_active_netsuite_credentials(workspace_id=2)
   netsuite_credentials.delete()

   response = api_client.post(url)
   assert response.status_code == 400
   assert response.data['message'] == 'NetSuite credentials not found in workspace'
