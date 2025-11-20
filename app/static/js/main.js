// Main JavaScript file
document.addEventListener("DOMContentLoaded", function () {
  console.log("HerbaTerra application loaded");

  // Initialize tooltips or other interactive elements here
});

// Example API call function
async function callHelloAPI(name = "World") {
  try {
    const response = await fetch(`/api/hello?name=${name}`);
    const data = await response.json();
    console.log(data.message);
    return data;
  } catch (error) {
    console.error("Error calling API:", error);
  }
}
