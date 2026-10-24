Feature: Managing contacts in the address book
  As a physician using the secure messaging system
  I want to find a contact, see who they are and write to them in a few gestures
  So that my address book helps me reach the right correspondent without mistakes

  Background:
    Given a physician's address book holding professionals and patients

  Scenario: Seeing a contact without leaving the list
    When the physician selects a contact in the address book
    Then the contact's details are shown next to the list on a computer
    And on a phone they open on their own page with a way back to the list
    And the details show the identity, the activity and every secure messaging address, the default one first

  Scenario: Writing to a contact from their details
    Given a contact with a default secure messaging address
    When the physician chooses to write to this contact
    Then a new message opens with the default address as recipient

  Scenario: Writing to a contact without a default address
    Given a contact with two secure messaging addresses and no default one
    When the physician chooses to write to this contact
    Then the physician chooses the address before the message opens

  Scenario: Understanding the marks on a contact
    Then a contact without any secure messaging address is marked "Sans adresse MSSanté"
    And a contact that comes from the national directory is marked "Annuaire"

  Scenario: Narrowing the list to contacts that need attention
    When the physician keeps only contacts without a secure messaging address
    Then only those contacts are listed, and their number is shown
    When the physician resets the filters
    Then the whole address book is listed again

  Scenario: Copying an address
    When the physician copies one of the contact's addresses
    Then the address is ready to be pasted and the physician is told so

  Scenario: Choosing the default address directly on the address
    Given a contact with two secure messaging addresses
    When the physician marks the second address as the default one and saves
    Then only the second address is offered when writing to this contact
    When the physician chooses that no address is the default one and saves
    Then every address of the contact is offered again when writing to this contact

  Scenario: A badly written address is refused
    When the physician types an address that is not an email address and saves
    Then the physician is told the address is not valid, next to it
    And the contact is not saved

  Scenario: An address outside the usual domain is accepted
    When the physician types a well-formed address from another trusted secure messaging domain
    Then the contact is saved with this address

  Scenario: The registration number of a directory contact cannot be changed
    Given a contact imported from the national directory with a registration number
    When the physician edits this contact
    Then the registration number is shown but cannot be changed
    And the physician is told it comes from the national directory

  Scenario: Leaving unsaved changes asks for confirmation
    Given the physician has changed a contact without saving
    When the physician tries to leave the contact
    Then the physician is asked whether to discard the changes
    When the physician chooses to keep editing
    Then the changes are still there

  Scenario: Leaving without changes does not ask anything
    Given the physician has opened a contact without changing anything
    When the physician leaves the contact
    Then no confirmation is asked
