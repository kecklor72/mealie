import type { UserTheme } from "~/lib/api/types/user";

export type ThemePreset = Omit<UserTheme, "id">;

/** Starting points for new themes. Users can tweak everything after picking one. */
export const THEME_PRESETS: ThemePreset[] = [
  {
    name: "Ocean",
    light: { primary: "#0077B6", secondary: "#023E8A", accent: "#00B4D8", success: "#2A9D8F", info: "#0096C7", warning: "#F4A261", error: "#E63946", background: "#F4FAFD", surface: "#FFFFFF" },
    dark: { primary: "#48CAE4", secondary: "#0096C7", accent: "#90E0EF", success: "#52B69A", info: "#4CC9F0", warning: "#F4A261", error: "#EF6F6C", background: "#0B1B26", surface: "#10263A" },
    fontBody: "Inter",
    fontHeading: "Inter",
    customCss: "",
  },
  {
    name: "Forest",
    light: { primary: "#2D6A4F", secondary: "#6B4226", accent: "#95A84F", success: "#40916C", info: "#457B9D", warning: "#DDA15E", error: "#BC4749", background: "#F5F7F2", surface: "#FFFFFF" },
    dark: { primary: "#74C69D", secondary: "#B08968", accent: "#B5C99A", success: "#52B788", info: "#8AB6D6", warning: "#E9C46A", error: "#E07A5F", background: "#141C17", surface: "#1B261F" },
    fontBody: "Lato",
    fontHeading: "Merriweather",
    customCss: "",
  },
  {
    name: "Lavender",
    light: { primary: "#7B5EA7", secondary: "#B5838D", accent: "#E5989B", success: "#4CAF50", info: "#6C8EBF", warning: "#F2A65A", error: "#D1495B", background: "#FAF7FC", surface: "#FFFFFF" },
    dark: { primary: "#C3A6E8", secondary: "#E5B3BB", accent: "#F4ACB7", success: "#81C784", info: "#9DB4E0", warning: "#F6BD60", error: "#EF7A85", background: "#1A1622", surface: "#241E2E" },
    fontBody: "Nunito",
    fontHeading: "Quicksand",
    customCss: "",
  },
  {
    name: "Tomato & Basil",
    light: { primary: "#C0392B", secondary: "#2E7D32", accent: "#F39C12", success: "#388E3C", info: "#1976D2", warning: "#F57C00", error: "#B71C1C", background: "#FFF9F3", surface: "#FFFFFF" },
    dark: { primary: "#FF6F59", secondary: "#81C784", accent: "#FFB74D", success: "#66BB6A", info: "#64B5F6", warning: "#FFA726", error: "#EF5350", background: "#1C1714", surface: "#26201C" },
    fontBody: "Source Sans 3",
    fontHeading: "Playfair Display",
    customCss: "",
  },
  {
    name: "Midnight",
    light: { primary: "#3F51B5", secondary: "#5C6BC0", accent: "#00BFA5", success: "#43A047", info: "#1E88E5", warning: "#FB8C00", error: "#E53935", background: "#F5F6FA", surface: "#FFFFFF" },
    dark: { primary: "#8C9EFF", secondary: "#7986CB", accent: "#64FFDA", success: "#69F0AE", info: "#82B1FF", warning: "#FFD180", error: "#FF8A80", background: "#0D0F1A", surface: "#161A2B" },
    fontBody: "DM Sans",
    fontHeading: "Space Grotesk",
    customCss: "",
  },
  {
    name: "High Contrast",
    light: { primary: "#000000", secondary: "#333333", accent: "#0050B3", success: "#006B1F", info: "#0050B3", warning: "#8A4B00", error: "#B00020", background: "#FFFFFF", surface: "#FFFFFF" },
    dark: { primary: "#FFD600", secondary: "#FFFFFF", accent: "#40C4FF", success: "#00E676", info: "#40C4FF", warning: "#FFAB00", error: "#FF5252", background: "#000000", surface: "#0A0A0A" },
    fontBody: "Atkinson Hyperlegible",
    fontHeading: "Atkinson Hyperlegible",
    customCss: "",
  },
];
