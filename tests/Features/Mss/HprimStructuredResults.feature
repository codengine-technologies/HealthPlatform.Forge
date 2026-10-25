Feature: Structured results of an HPRIM laboratory report
  As a physician using the secure messaging system
  I want the structured lines of an HPRIM report to become biology results
  So that I can follow them and be alerted on abnormal values like any other biology report

  Background:
    Given a physician's mailbox

  Scenario: Structured lines become biology results
    When a laboratory sends an HPRIM report with structured result lines
    Then each line becomes a biology result with its value, unit and normal range

  Scenario: A report without structured lines stays a text document
    When a laboratory sends an HPRIM report with free text only
    Then the biology document has no structured result

  Scenario: The laboratory flags a result as abnormal
    When a result line carries an abnormal indicator from the laboratory
    Then the result is flagged as abnormal

  Scenario: An out-of-range value without indicator is flagged
    When a numeric result outside its normal range carries no indicator
    Then the result is flagged as abnormal

  Scenario: A qualitative value without indicator is not flagged
    When a text result carries no indicator
    Then the result is not flagged as abnormal

  Scenario: Abnormal results raise the alert once the report is attached
    Given an HPRIM report with an abnormal result
    When the physician attaches it to a patient
    Then the patient appears among the patients with abnormal unread results

  Scenario: A partial result is marked as such
    When a result line is marked as partial by the laboratory
    Then the result is shown as partial

  Scenario: Nothing is replaced before the report is attached
    Given a partial HPRIM report received and not yet attached
    When the laboratory sends the completed report for the same request
    Then both reports are waiting to be attached
    And the first one is still shown as partial

  Scenario: Laboratory codes are not mixed with standard codes
    Given a patient with a standard-coded result for an examination
    When an HPRIM result for the same examination is attached to that patient
    Then the two results are shown as separate series

  Scenario: Structured results in a delegated mailbox are shown but never stored
    Given a physician who has delegated her mailbox to a colleague
    And she receives an HPRIM report with a value outside its normal range
    When the colleague opens that report in the delegated mailbox
    Then the colleague sees the results with the abnormal value highlighted
    But no biology result is stored for the colleague
    And the patient does not appear in the colleague's abnormal results
