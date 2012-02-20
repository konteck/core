Python WSGI micro framework
Core functionality can be extended by "Monkey Patching"

## Installation

```
pip install core
```

## Usage

app.py

```python

from core import app

app = app(__name__)

# Set site locale
app.locale(app.config.LANG)

@app.view('main.html')
@app.route('/')
def home():
    return {
        'home_news': {}
    } 

app.run(host='127.0.0.1', port=8080)       

```

That's it!