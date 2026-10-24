Feature: A message without any text written leaves no draft
  As a physician writing secure messages
  I want a message I did not write anything in to close without a question and without a draft
  So that my drafts only hold the messages I actually started

  Scenario: Closing a new message with nothing written asks nothing
    Given the physician opens a new message
    When the physician closes it without writing anything
    Then no question about a draft is asked
    And no draft is kept

  Scenario: A recipient and a subject alone do not make a draft
    Given the physician opens a new message
    And chooses a recipient and types a subject
    When the physician closes it without writing in the body
    Then no question about a draft is asked
    And no draft is kept

  Scenario: Waiting does not create a draft of an empty message
    Given the physician opens a new message and writes nothing in the body
    When more than half a minute passes
    Then no draft is kept

  Scenario: A reply left without writing leaves nothing
    Given the physician opens a reply to a message
    When the physician closes it without writing anything
    Then no question is asked and no draft is kept

  Scenario: A signature alone is not a written message
    Given the physician's signature is added to a new message
    When the physician closes it without writing anything
    Then no draft is kept

  Scenario: A message with written text keeps its draft as before
    Given the physician writes a sentence in a new message
    When the physician closes it
    Then the draft is kept as before

  Scenario: A saved draft emptied of its text is not lost silently
    Given a saved draft that the physician reopens
    When the physician erases all its text and closes it
    Then the saved draft is not overwritten with an empty one
