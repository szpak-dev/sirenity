Feature: Public Siren document
  Scenario: Invalid relation is rejected
    Given an invalid public Siren relation
    When the caller creates its link
    Then the public boundary rejects the relation

  Scenario: Official document serializes through the public API
    Given an official public Siren document
    When the caller serializes the document
    Then the payload contains only official members
