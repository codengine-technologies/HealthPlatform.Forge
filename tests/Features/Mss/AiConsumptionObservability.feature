Feature: AI consumption observability
  As the operations team
  I want every AI call attributed to the feature that triggered it
  So that we can find which uses consume the most tokens and optimise costs

  Scenario: Tokens are counted per feature
    Given the spelling correction asks the AI provider to correct a text
    And the provider reports 120 input tokens and 40 output tokens
    When the operations team reads the consumption measures
    Then 120 input and 40 output tokens are counted for "correction-orthographe"

  Scenario: Each call leaves one trace without health data
    Given an incoming mail is tagged by the AI
    When the call completes
    Then one trace names the feature, the model, the token counts, the duration and the mail identifier
    And it contains no mail content, address or patient identifier

  Scenario: An interrupted call is still counted
    Given a dictation correction stream is cancelled before its end
    When the operations team reads the consumption measures
    Then the call is counted for "correction-dictee" with an unknown usage

  Scenario: A call without a feature is never lost
    Given an AI call made outside any known feature
    When it completes
    Then its tokens are counted under "non-attribue"
