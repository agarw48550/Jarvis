/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/**/*.{js,jsx,ts,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    50: '#eef2ff',
                    500: '#6366f1',
                    600: '#4f46e5',
                    900: '#312e81',
                },
                dark: {
                    50: '#f8fafc',
                    800: '#1e293b',
                    900: '#0f172a',
                    950: '#020617',
                }
            },
            backdropBlur: {
                xs: '2px',
            }
        },
    },
    plugins: [],
}
