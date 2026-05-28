#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
method="${UPLOAD_METHOD}"
upload_dir="${UPLOAD_PATH}" 
user="${ENDPOINT_USER}"
password="${ENDPOINT_PASSWORD}"
graph_name="${ENDPOINT_GRAPH}"
endpoint_url="${ENDPOINT_URL}"

# Define the temporary combined file
COMBINED_FILE="combined_data.ttl"

# --- Validation ---
if [ -z "$method" ] || [ -z "$upload_dir" ] || [ -z "$user" ] || [ -z "$password" ] || [ -z "$endpoint_url" ]; then
  echo "Error: One or more required environment variables are not set."
  echo "Please check UPLOAD_METHOD, UPLOAD_PATH, ENDPOINT_USER, ENDPOINT_PASSWORD, and ENDPOINT_URL."
  echo "Current Target Environment: ${TARGET_ENV}"
  exit 1
fi

echo "-----------------------------------------"
echo "Starting file consolidation and upload process..."
echo "Environment: ${CI_ENVIRONMENT_NAME}"
echo "Method: ${method}"
echo "Source Directory: ${upload_dir}"
echo "Endpoint: ${endpoint_url}"
echo "Graph: ${graph_name}"
echo "-----------------------------------------"

# --- Consolidation ---

# 1. Find all .ttl files
shopt -s nullglob 
files_to_combine=(${upload_dir}/*.ttl)
shopt -u nullglob # Disable nullglob

if [ ${#files_to_combine[@]} -eq 0 ]; then
    echo "Warning: No '.ttl' files found in '${upload_dir}'. Exiting successfully."
    exit 0
fi

echo "Found ${#files_to_combine[@]} .ttl file(s) to combine."

# 2. Concatenate all files into the single temporary file
cat "${files_to_combine[@]}" > "${COMBINED_FILE}"

echo "All files successfully combined into ${COMBINED_FILE}."

# --- Execution ---

# 3. Upload the single combined file
echo "--- Uploading combined file: ${COMBINED_FILE} ---"

response_code=$(curl --silent --show-error --fail \
    -X "${method}" \
    -H "Content-Type: text/turtle" \
    -T "${COMBINED_FILE}" \
    -u "${user}:${password}" \
    --write-out "%{http_code}" \
    "${endpoint_url}?graph=${graph_name}")

echo "Upload complete. Server responded with HTTP code: ${response_code}"

# Check for success codes: 200 (OK), 201 (Created), 204 (No Content)
if [[ $response_code != "200" ]] && [[ $response_code != "201" ]] && [[ $response_code != "204" ]]; then
    echo "!!!! Upload logic FAILED. Response code: ${response_code}"
    # Remove the temporary file before exiting with error
    rm -f "${COMBINED_FILE}" 
    exit 1 
fi

echo "✅ Success: Combined file upload confirmed."

# 4. Cleanup
rm -f "${COMBINED_FILE}"
echo "Cleanup complete: Removed temporary file ${COMBINED_FILE}."