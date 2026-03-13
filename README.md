# GSU_TECH_03132026

This project contains a client and a server application.

## Running with Docker

To run the entire system with Docker, make sure you have Docker and Docker Compose installed.

1.  **Create a `.env` file** in the root of the project and populate it with the necessary environment variables. You can use the `.env.template` file in the `server` directory as a reference.

2.  **Run the application** using Docker Compose:

    ```bash
    docker-compose up --build
    ```

This will build the Docker images for the client and server and start the services.

*   The client will be available at [http://localhost:5173](http://localhost:5173)
*   The server will be available at [http://localhost:5000](http://localhost:5000)
