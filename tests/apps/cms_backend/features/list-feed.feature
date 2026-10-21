Feature: List feed
  In order to have feeds in the platform
  I want list all feeds

  Scenario: When there are feeds
    Given There are feeds:
      | id                                   | title            | description                    | author | source   | createdAt                | category      | url                                                     |
      | de32eacb-1ce8-408f-b07b-8c3b0e0437c0 | Test Feed Find   | Description - Test Feed Find   | Ivan   | CMS      | 2023-06-16T14:58:39.733Z | POLITICS      |                                                         |
      | 2305ecd9-068d-45bc-ada8-c6778ecf863e | Test Feed Find 2 | Description - Test Feed Find 2 | Ivan   | CMS      | 2023-06-18T14:58:39.733Z | CULTURE       |                                                         |
      | aacff872-8f95-43ad-9434-076befee22ee | Test Feed Find 1 | Description - Test Feed Find 1 | Ivan   | EL_PAIS  | 2023-06-17T14:58:39.733Z | INTERNATIONAL |                                                         |
      | e5cb161a-6e75-4b67-acde-b323d64c0339 | Test Feed Find 3 | Description - Test Feed Find 3 | Ivan   | CMS      | 2023-06-19T14:58:39.733Z | OTHER         |                                                         |
      | 798516e0-ee38-4a64-a0be-f3af830d8815 | Test Feed Find 4 | Description - Test Feed Find 4 | Ivan   | EL_MUNDO | 2023-06-20T14:58:39.733Z | SPORTS        | https://www.elmundo.es/deportes/2023/06/20/noticia.html |
    When I send a GET request to "/feed/list"
    Then The response status code should be 200
    And The response should contains:
      """
      {
      "items": [
        {
            "id": "798516e0-ee38-4a64-a0be-f3af830d8815",
            "title": "Test Feed Find 4",
            "description": "Description - Test Feed Find 4",
            "author": "Ivan",
            "source": "EL_MUNDO",
            "category": "SPORTS",
            "url": "https://www.elmundo.es/deportes/2023/06/20/noticia.html"
        },
        {
            "id": "e5cb161a-6e75-4b67-acde-b323d64c0339",
            "title": "Test Feed Find 3",
            "description": "Description - Test Feed Find 3",
            "author": "Ivan",
            "source": "CMS",
            "category": "OTHER",
            "url": null
        },
        {
            "id": "2305ecd9-068d-45bc-ada8-c6778ecf863e",
            "title": "Test Feed Find 2",
            "description": "Description - Test Feed Find 2",
            "author": "Ivan",
            "source": "CMS",
            "category": "CULTURE",
            "url": null
        },
        {
            "id": "aacff872-8f95-43ad-9434-076befee22ee",
            "title": "Test Feed Find 1",
            "description": "Description - Test Feed Find 1",
            "author": "Ivan",
            "source": "EL_PAIS",
            "category": "INTERNATIONAL",
            "url": null
        },
        {
            "id": "de32eacb-1ce8-408f-b07b-8c3b0e0437c0",
            "title": "Test Feed Find",
            "description": "Description - Test Feed Find",
            "author": "Ivan",
            "source": "CMS",
            "category": "POLITICS",
            "url": null
        }
      ],
      "next_cursor": null
      }
      """

  Scenario: When there are feeds of the requested category
    Given There are feeds:
      | id                                   | title            | description                    | author | source   | createdAt                | category | url                                                     |
      | de32eacb-1ce8-408f-b07b-8c3b0e0437c0 | Test Feed Find   | Description - Test Feed Find   | Ivan   | CMS      | 2023-06-16T14:58:39.733Z | SPORTS   |                                                         |
      | 2305ecd9-068d-45bc-ada8-c6778ecf863e | Test Feed Find 2 | Description - Test Feed Find 2 | Ivan   | CMS      | 2023-06-18T14:58:39.733Z | CULTURE  |                                                         |
      | 798516e0-ee38-4a64-a0be-f3af830d8815 | Test Feed Find 4 | Description - Test Feed Find 4 | Ivan   | EL_MUNDO | 2023-06-20T14:58:39.733Z | SPORTS   | https://www.elmundo.es/deportes/2023/06/20/noticia.html |
    When I send a GET request to "/feed/list?category=SPORTS"
    Then The response status code should be 200
    And The response should contains:
      """
      {
      "items": [
        {
            "id": "798516e0-ee38-4a64-a0be-f3af830d8815",
            "title": "Test Feed Find 4",
            "source": "EL_MUNDO",
            "category": "SPORTS",
            "url": "https://www.elmundo.es/deportes/2023/06/20/noticia.html"
        },
        {
            "id": "de32eacb-1ce8-408f-b07b-8c3b0e0437c0",
            "title": "Test Feed Find",
            "source": "CMS",
            "category": "SPORTS",
            "url": null
        }
      ],
      "next_cursor": null
      }
      """

  Scenario: When the category is not a known value
    When I send a GET request to "/feed/list?category=sports"
    Then The response status code should be 400

  Scenario: When there are not any feeds
    When I send a GET request to "/feed/list"
    Then The response status code should be 200
    And The response should be:
    """
        {"items": [], "next_cursor": null}
    """

  Scenario: Browsing the feeds page by page
    Given There are feeds:
      | id                                   | title  | description          | author | source   | createdAt                | category |
      | 0b6c1a52-3d0e-4c1b-9d3e-0f3b7c1a2b01 | Feed 1 | Description - Feed 1 | Ivan   | CMS      | 2023-06-16T14:58:39.733Z | POLITICS |
      | 0b6c1a52-3d0e-4c1b-9d3e-0f3b7c1a2b02 | Feed 2 | Description - Feed 2 | Ivan   | EL_MUNDO | 2023-06-17T14:58:39.733Z | SPORTS   |
      | 0b6c1a52-3d0e-4c1b-9d3e-0f3b7c1a2b03 | Feed 3 | Description - Feed 3 | Ivan   | EL_PAIS  | 2023-06-18T14:58:39.733Z | CULTURE  |
    When I send a GET request to "/feed/list?limit=2"
    Then The response status code should be 200
    And The response should contains:
      """
      {
        "items": [
          {"id": "0b6c1a52-3d0e-4c1b-9d3e-0f3b7c1a2b03", "title": "Feed 3"},
          {"id": "0b6c1a52-3d0e-4c1b-9d3e-0f3b7c1a2b02", "title": "Feed 2"}
        ]
      }
      """
    When I request the next page
    Then The response status code should be 200
    And The response should contains:
      """
      {
        "items": [
          {"id": "0b6c1a52-3d0e-4c1b-9d3e-0f3b7c1a2b01", "title": "Feed 1"}
        ],
        "next_cursor": null
      }
      """
