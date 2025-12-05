# KEYBOARD-SMASHERS-310
Our COSC310 final project, based upon movie-reviews. 

-------------------------------------------------------------------------

Project Overview

Our project is a community-driven movie review website where people can sign up, check out movies, and share their thoughts about them. It's pretty straightforward, basically think of it like a smaller, simpler version of IMDb or Letterboxd.

What users can do:
    Create an account and log in
    Browse through our movie database
    Read reviews from other users
    Write their own reviews for movies they've watched

What admins can do:
    Everything regular users can do, plus more
    Import new movies from external databases to keep our collection growing
    Moderate reviews by giving out penalties if someone's being inappropriate or breaking the rules

-------------------------------------------------------------------------

Architecture 

We chose to do a layered architecture to keep our code organized, maintainable, and easily updateable. The system is structured with three main layers: Controllers(Which contain logic and handle API requests), DAO's(Data Access Objects which handle the reading and writing of our database), and Models(which represent our actual entities such as users, movies, reviews, etc...). 
When a user would make an API request from the front end, it would typically follow this flow: the request hits a FastAPI route endpoint, which calls the necessary controller method. The controller validates the request, applies any business logic (like checking if a user is a admin before allowing movie imports), and then interacts with the DAO to read or modify data. The DAO manages all the CSV file operations and converts the CSV data into Model objects (like for example a user instance) that represent our entities with the correct attributes and methods. These models are then passed back through the controller, converted to API schemas (Pydantic models for JSON serialization), and returned to the frontend as JSON responses. 

-------------------------------------------------------------------------

How to run
        -Copy the url from this projects github repository page
        -Open VS code
        -Hit ctrl+shift+p
        -Type "git: clone"
        -Paste url address into text bar and hit enter
        -Select a folder of your choosing to clone into
        -Let all files appear
        -Go into root directories .env file 
        -Find where it says "TMDB_API_KEY=replacemeplease"
        -Replace the "replacemeplease" with the API key sent in the submission document
        -Save all files
        -Open the terminal
        -Ensure docker desktop is open
        -Run the command "docker-compose up --build"
        -Open your favourite search thingy
        -In the first tab put this into the url address bar "http://localhost:3000" (This is the front end)
        -In the second tab put this into the url address bar "http://localhost:8000" (This is the back end)
        -In the third tab put this into the url address bar "http://localhost:8000/docs" (This is the API Documentation)
        -Have fun!
        -Note: to end this go back to your terminal and paste "docker-compose down"



