from app import create_app

# Create an instance of the application
app = create_app()

# This block allows you to run the server by executing "python run.py"
if __name__ == '__main__':
    app.run(debug=True)