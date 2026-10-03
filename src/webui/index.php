<?php
/**
 * Tailscale TOS5 Web UI
 * Authentication wrapper + React app loader
 */

define('MODULE_NAME', 'Tailscale');

// Authentication check
session_start();
if (!((isset($_SESSION['kod_user']['role']) && $_SESSION['kod_user']['role'] === 'root') ||
      (isset($_SESSION['muser']) && $_SESSION['muser'] === 'admin'))) {
    die('Access denied - you need to login to TOS with an admin account');
}
?>
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Tailscale</title>
    <link rel="icon" type="image/png" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAACXBIWXMAAAsTAAALEwEAmpwYAAABhklEQVR4nO2WO07DQBCGP0hBQUFBh0RBQUFJQUFJSUNBQ0NBQ0FJQ0FJSUFDQ0NBQ0NDQ0FBQ0NDQ0FBQ0NDYyT+SCtlZe9jHYdI/NIqyu7M/J6d2V0I+C8UAIqZbAIHwCVwA1SBJ6AX+AIUgD3gAKgDN8A18Ow3YQI4AgqAAXR5YwCUgVPgIK7AHHABHSC0wFfAAVAFavHnwBFQAoaBMrAL5IAKsAsMx7UTAzgGBoBqDNBOuwVkYu8c2AYG4wAJ4ARIx9/5hOJh4BAYjCMwAlSAYvx9OoHCMXAATMYBGMAdMBCnXwP7wGgcoA1wHt/NOHH9CjgDJuIAj8BDnI0mcAFMxwFugavYux7XboD5OMALcBu7p8AlsBgHuAfuYgvVgctYIM7wCjzFFlqJBR6ARsLaLbCSBGgBLYlrMwkBVoFO0loSYC3hv3MS4MukAGfARlKA52ArCfABbCcFaAJ7SYAy8JgU4ARwE+iIfxfAU5KjDeSArYQCbSAL5C0EsiHQPxUbAv0B+QXp4KHZy1LdFwAAAABJRU5ErkJggg==" />
    <script type="module" crossorigin src="./dist/assets/index.js"></script>
    <link rel="stylesheet" crossorigin href="./dist/assets/index.css">
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
