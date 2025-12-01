# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Testing the ODD-Compliant Road Network Demo

To verify that the ODD (Operational Design Domain) filtering is working correctly, follow this test scenario:

### Quick Test Scenario (Pittsburgh Region)

1. **Select a Region**: Navigate to Pittsburgh, PA on the map
2. **Enable Road Features**: Toggle on the "Road Features" layer in the sidebar
3. **Configure ODD Filters**:
   - Select **"Live"** ODD Type (Important: Do NOT use "All" as it bypasses filtering)
   - Apply the following filters:
     - `highway_type`: Select only **"residential"**
     - `speed_limit`: Set to **25** mph
     - `is_major_road`: Set to **False**
     - `traffic_signals`: Set to **False**
4. **Generate Network**: Click the "Generate Network" button
5. **Observe Results**:
   - The filtered ODD-compliant network will appear as **green lines**
   - The complete unfiltered road network appears as **blue lines**
   - The green network should be noticeably smaller, showing only residential streets without traffic signals

### Expected Behavior

- **Green lines** = ODD-compliant roads matching your filter criteria
- **Blue lines** = Complete unfiltered road network
- The green network should be a subset of the blue network
- Changing filters and regenerating should produce different green networks

### Troubleshooting

If the road network doesn't change when you apply filters:
- Verify that **"Live"** ODD Type is selected (not "All")
- Ensure you clicked "Generate Network" after changing filters
- Check the browser console for any errors
- Try the test scenario above for a clear visual difference

## Available Scripts

If you want to specify backend URL and PORT, in an local `.env` file, provide:
- REACT_APP_BACKEND_URL
- REACT_APP_BACKEND_PORT


In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
