Feature: Create feed
  In order to have feeds in the platform
  I want to create feeds
  
  Scenario: When a feed does not exist
    When I send a PUT request to "/feed/04deff28-6c34-4634-a7c8-a4a09dabd87a" with body:
      """
      {
        "title": "Example Title",
        "description": "Example Description",
        "author": "Ivan",
        "category": "SPORTS"
      }
      """
    Then The response status code should be 201
    And The response should contains:
      """
      {
        "id": "04deff28-6c34-4634-a7c8-a4a09dabd87a",
        "title": "Example Title",
        "description": "Example Description",
        "author": "Ivan",
        "source": "CMS",
        "category": "SPORTS",
        "url": null
      }
      """


  Scenario: When a feed exists
    Given There are feeds:
    | id                                   | title           | description           | author | source | category |
    | 749dbded-bae2-43ac-9537-0d71bddb6f9a | Example Title 1 | Example Description 2 | Ivan   | CMS    | POLITICS |
    When I send a PUT request to "/feed/749dbded-bae2-43ac-9537-0d71bddb6f9a" with body:
      """
      {
        "title": "Example Title 3",
        "description": "Example Description 3",
        "author": "Ivan",
        "category": "CULTURE"
      }
      """
    Then The response status code should be 409
    And The response should be:
      """
      {
        "error": "Feed with id <749dbded-bae2-43ac-9537-0d71bddb6f9a> already exists"
      }
      """