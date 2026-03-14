// frontend/src/App.js
import React, { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [data, setData] = useState(null);

  useEffect(() => {
    axios
      .get("http://localhost:8000/api/data")
      .then((response) => setData(response.data))
      .catch((error) => console.error(error));
  }, []);

  return (
    <div className="App">
      <h1>React + Python</h1>
      {data && (
        <p>
          {data.message}: {JSON.stringify(data.data)}
        </p>
      )}
    </div>
  );
}

export default App;
