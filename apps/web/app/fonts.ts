import { Fraunces, Hanken_Grotesk, IBM_Plex_Mono } from "next/font/google";

// The CSS variable names match FONT_VARIABLES in scripts/generate-tokens.mjs.
export const fraunces = Fraunces({
  subsets: ["latin"],
  axes: ["opsz"],
  style: ["normal", "italic"],
  variable: "--font-fraunces",
  display: "swap",
});

export const hankenGrotesk = Hanken_Grotesk({
  subsets: ["latin"],
  variable: "--font-hanken",
  display: "swap",
});

export const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const fontVariables = [fraunces.variable, hankenGrotesk.variable, plexMono.variable].join(
  " ",
);
