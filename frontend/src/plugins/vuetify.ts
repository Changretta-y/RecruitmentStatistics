import "vuetify/styles";
import "@mdi/font/css/materialdesignicons.css";

import { createVuetify } from "vuetify";
import { aliases, mdi } from "vuetify/iconsets/mdi";

export const vuetify = createVuetify({
  theme: {
    defaultTheme: "campus",
    themes: {
      campus: {
        dark: false,
        colors: {
          primary: "#3157d5",
          secondary: "#0f766e",
          accent: "#f59e0b",
          background: "#f5f7fb",
          surface: "#ffffff",
          "surface-variant": "#e8edf7",
          error: "#b42318",
          success: "#087443",
          info: "#0f6cbd",
        },
      },
    },
  },
  icons: {
    defaultSet: "mdi",
    aliases,
    sets: { mdi },
  },
  defaults: {
    VBtn: { rounded: "lg", elevation: 0 },
    VCard: { rounded: "xl" },
    VTextField: { variant: "outlined", density: "comfortable", color: "primary" },
    VSelect: { variant: "outlined", density: "comfortable", color: "primary" },
    VTextarea: { variant: "outlined", density: "comfortable", color: "primary" },
  },
});

export default vuetify;
