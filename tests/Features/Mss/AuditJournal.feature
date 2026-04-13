Feature: MSS Audit Journal
  As a healthcare professional using the secure messaging system
  I want all mail actions to be traced in an audit journal
  So that I can review and comply with regulatory requirements

  Background:
    Given I am authenticated as a valid MSS user
    And the audit service is running

  # --- API: Audit trace retrieval ---

  Scenario: Retrieve paginated audit traces
    Given there are 120 audit traces in the database
    When I request audit traces with page 0 and pageSize 50
    Then the response status code is 200
    And the result contains 50 traces
    And the total count is 120
    And the total pages is 3

  Scenario: Retrieve audit traces filtered by action type
    Given there are audit traces for actions "MailSend" and "MailDelete"
    When I request audit traces with actionType "MailSend"
    Then the response status code is 200
    And all returned traces have actionType "MailSend"

  Scenario: Retrieve audit traces filtered by date range
    Given there are audit traces from "2025-01-01" to "2025-06-30"
    When I request audit traces with dateFrom "2025-03-01" and dateTo "2025-03-31"
    Then the response status code is 200
    And all returned traces have timestamps within the range

  Scenario: Retrieve audit traces filtered by success status
    Given there are successful and failed audit traces
    When I request audit traces with success "false"
    Then the response status code is 200
    And all returned traces have success equal to false

  Scenario: Retrieve audit traces filtered by mail message ID
    Given there are audit traces for message ID "<msg-001@example.com>"
    When I request audit traces with mailMessageId "<msg-001@example.com>"
    Then the response status code is 200
    And all returned traces have mailMessageId "<msg-001@example.com>"

  Scenario: Retrieve audit traces with free text search
    Given there are audit traces with subject containing "Résultats laboratoire"
    When I request audit traces with search "laboratoire"
    Then the response status code is 200
    And returned traces contain the search term in subject or error message

  Scenario: Retrieve a single audit trace by ID
    Given there is an audit trace with ID 42
    When I request audit trace with ID 42
    Then the response status code is 200
    And the trace ID is 42
    And all fields including serverRequest and serverResponse are not truncated

  Scenario: Retrieve a non-existent audit trace returns 404
    When I request audit trace with ID 999999
    Then the response status code is 404

  Scenario: Unauthenticated request returns 401
    Given I am not authenticated
    When I request audit traces with page 0 and pageSize 50
    Then the response status code is 401

  # --- Instrumentation: Mail send ---

  Scenario: Sending an email produces a MailSend audit trace
    When I send an email to "dest@example.com" with subject "Test audit"
    Then a new audit trace is created with actionType "MailSend"
    And the trace has success equal to true
    And the trace contains the subject "Test audit"
    And the trace contains toAddresses "dest@example.com"

  Scenario: Failed email send produces a MailSend error trace
    Given the SMTP server is unavailable
    When I attempt to send an email to "dest@example.com"
    Then a new audit trace is created with actionType "MailSend"
    And the trace has success equal to false
    And the trace contains an error message

  # --- Instrumentation: Mail delete ---

  Scenario: Deleting an email produces a MailDelete audit trace
    Given there is an email with UID 100 in folder "INBOX"
    When I delete email UID 100 from folder "INBOX"
    Then a new audit trace is created with actionType "MailDelete"
    And the trace has success equal to true
    And the trace has mailUid 100
    And the trace has folderPath "INBOX"

  Scenario: Bulk deleting emails produces individual audit traces
    Given there are emails with UIDs 101, 102, 103 in folder "INBOX"
    When I bulk delete emails 101, 102, 103 from folder "INBOX"
    Then 3 audit traces are created with actionType "MailDelete"
    And each trace has success equal to true

  # --- Instrumentation: Mail move ---

  Scenario: Moving an email produces a MailMove audit trace
    Given there is an email with UID 200 in folder "INBOX"
    When I move email UID 200 from "INBOX" to "Archives"
    Then a new audit trace is created with actionType "MailMove"
    And the trace has success equal to true
    And the trace has folderPath "INBOX -> Archives"

  Scenario: Bulk moving emails produces individual audit traces
    Given there are emails with UIDs 201, 202 in folder "INBOX"
    When I bulk move emails 201, 202 from "INBOX" to "Archives"
    Then 2 audit traces are created with actionType "MailMove"

  # --- Instrumentation: Mail read / flag ---

  Scenario: Marking an email as read produces a MailRead audit trace
    Given there is an unread email with UID 300 in folder "INBOX"
    When I mark email UID 300 as read in folder "INBOX"
    Then a new audit trace is created with actionType "MailRead"
    And the trace has success equal to true

  Scenario: Flagging an email produces a MailFlagChange audit trace
    Given there is an email with UID 400 in folder "INBOX"
    When I flag email UID 400 in folder "INBOX"
    Then a new audit trace is created with actionType "MailFlagChange"
    And the trace has success equal to true

  # --- Instrumentation: Read receipt ---

  Scenario: Sending a read receipt produces a ReadReceiptSend audit trace
    Given there is an email with UID 500 requesting a read receipt
    When I send a read receipt for email UID 500
    Then a new audit trace is created with actionType "ReadReceiptSend"
    And the trace has success equal to true
    And the trace has mailMessageId set

  # --- Audit timeline ---

  Scenario: Email timeline shows all actions for a given message ID
    Given an email with message ID "<thread-001@example.com>" was sent, read, and moved
    When I request audit traces with mailMessageId "<thread-001@example.com>"
    Then the result contains at least 3 traces
    And the traces are ordered by timestamp ascending
    And the trace actions include "MailSend", "MailRead", and "MailMove"

  # --- Truncation ---

  Scenario: List view truncates serverRequest and serverResponse
    Given there is an audit trace with serverRequest longer than 500 characters
    When I request audit traces with page 0 and pageSize 50
    Then the serverRequest field in the list is at most 500 characters
    And the serverResponse field in the list is at most 500 characters

  Scenario: Detail view returns full serverRequest and serverResponse
    Given there is an audit trace with ID 55 and serverRequest longer than 500 characters
    When I request audit trace with ID 55
    Then the serverRequest field contains the full content
    And the serverResponse field contains the full content
