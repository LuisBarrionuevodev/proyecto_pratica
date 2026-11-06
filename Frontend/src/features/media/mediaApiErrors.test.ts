import { describe, expect, it } from "vitest";

import {
  isMediaUnreadableLocalFileError,
  isMediaUnreadableLocalFileMessage,
  mediaErrorMessageFromUnknown,
} from "./mediaApiErrors";
import { MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE } from "./utils/mediaUploadMessages";

describe("mediaApiErrors — archivo ilegible (Google Fotos)", () => {
  it("traduce NotReadableError al mensaje operativo", () => {
    const err = new DOMException(
      "The requested file could not be read, typically due to permission problems that have occurred after a reference to a file was acquired from.",
      "NotReadableError"
    );
    expect(mediaErrorMessageFromUnknown(err)).toBe(MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE);
    expect(mediaErrorMessageFromUnknown(err)).not.toMatch(/requested file could not be read/i);
  });

  it("detecta el texto de Chrome aunque el name no sea NotReadableError", () => {
    const err = new Error(
      "The requested file could not be read, typically due to permission problems that have occurred after a reference to a file was acquired from."
    );
    expect(isMediaUnreadableLocalFileError(err)).toBe(true);
    expect(mediaErrorMessageFromUnknown(err)).toBe(MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE);
  });

  it("detecta permission problems + reference to a file", () => {
    const err = new Error("Failed: permission problems after a reference to a file was acquired");
    expect(mediaErrorMessageFromUnknown(err)).toBe(MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE);
  });

  it("no traduce errores de red", () => {
    expect(mediaErrorMessageFromUnknown(new Error("Network Error"))).toBe(
      "Error de red al subir el archivo."
    );
  });

  it("isMediaUnreadableLocalFileMessage cubre el texto ya traducido", () => {
    expect(isMediaUnreadableLocalFileMessage(MEDIA_UNREADABLE_LOCAL_FILE_MESSAGE)).toBe(true);
    expect(isMediaUnreadableLocalFileMessage("Error de red al subir el archivo.")).toBe(false);
  });
});
