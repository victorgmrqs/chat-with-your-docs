// Runs before src/test/setup.ts. Uploads need one consistent set of Blob, File, FormData and
// Request, as a browser has. Vitest's jsdom environment mixes jsdom's Blob/File/FormData with
// Node's fetch through a compat Request that copies jsdom files into plain Blobs, dropping the
// file name, and the multipart body never reaches MSW. Tests use Node's classes throughout.
import { Blob, File } from 'node:buffer'

// Node's FormData is not exported by name; Node's Response (not replaced by jsdom) hands one out.
const FormData = (await new Response(new URLSearchParams()).formData()).constructor
// Vitest's compat Request extends Node's; without the compat layer this is Function.prototype.
const compatParent: unknown = Object.getPrototypeOf(globalThis.Request)
const Request = compatParent === Function.prototype ? globalThis.Request : compatParent

Object.assign(globalThis, { Blob, File, FormData, Request })
