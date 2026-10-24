Feature: Receiving a laboratory result in HPRIM format
  As a physician using the secure messaging system
  I want the laboratory results sent in the legacy HPRIM format to be read
  So that they become biology documents instead of unreadable technical files

  Background:
    Given a physician's mailbox

  Scenario: A mail carrying an HPRIM result becomes a biology document
    When a laboratory sends a mail with an HPRIM result file
    Then a biology document is created from that result
    And it is waiting to be attached to a patient

  Scenario: One HPRIM file carrying several results
    When a laboratory sends one HPRIM file holding results for two patients
    Then two separate biology documents are created

  Scenario: The PDF sent with the result is kept with it
    When the HPRIM result comes with a PDF report
    Then the PDF is available from the biology document

  Scenario: A structured report takes precedence over the HPRIM file
    When a mail carries both a valid structured biology report and an HPRIM file
    Then only the structured report becomes a biology document

  Scenario: The HPRIM file is used when the structured report is unreadable
    When a mail carries an unreadable structured biology report and an HPRIM file
    Then the biology document is created from the HPRIM file

  Scenario: A result received twice is never hidden on reception
    Given an HPRIM result already received and not yet attached
    When the laboratory sends the same result again
    Then both documents are waiting to be attached
    And none of them is flagged as a duplicate

  Scenario: A file that is not a real HPRIM result stays a plain attachment
    When a mail carries an .hpm file without the HPRIM end markers
    Then no biology document is created
    And the file remains a plain attachment of the mail

  Scenario: The HPRIM text is never shown as the mail body
    When a mail carries an HPRIM file and no other text
    Then the mail body is empty rather than the raw HPRIM text
