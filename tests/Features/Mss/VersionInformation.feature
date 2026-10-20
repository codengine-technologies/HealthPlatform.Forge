Feature: Mail server version information
  As a healthcare professional using the secure messaging
  I want to see which version of the mail server I am using
  So that support can identify exactly what is deployed when I report a problem

  Scenario: The settings page shows the mail server version
    Given a practitioner signed in to the messaging
    When they open the settings page
    Then at the bottom they see the mail server version, its build date and its environment
    And the application does not show a version of its own

  Scenario: The build date is shown in French local time
    Given the mail server was built on 19 October 2026 at 07:05 UTC
    When the practitioner opens the settings page
    Then the server build date reads "19/10/2026 à 09:05"

  Scenario: The server is unreachable
    Given a practitioner signed in to the messaging
    And the mail server cannot be reached
    When they open the settings page
    Then the mail server line says the information is unavailable

  Scenario: Version information is not disclosed without a session
    Given someone who is not signed in
    When they ask the mail server for its version
    Then the request is refused
    And no version information is revealed
