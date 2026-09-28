import { copyFileSync, mkdirSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import { deflateRawSync } from "node:zlib";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourceRoot = path.join(repoRoot, "frontend", "src", "browser-extension");
const outputPath = path.join(
  repoRoot,
  "artifacts",
  "recruitment-capture-extension-v0.1.0.zip",
);
const runtimeFiles = [
  "core.js",
  "manifest.json",
  "popup.css",
  "popup.html",
  "popup.js",
  "service-worker.js",
];
const requiredOrigin = "http://115.190.240.84:5173/*";

const manifest = JSON.parse(readFileSync(path.join(sourceRoot, "manifest.json"), "utf8"));
if (manifest.manifest_version !== 3) {
  throw new Error("The extension manifest must use Manifest V3.");
}
if (!manifest.host_permissions?.includes(requiredOrigin)) {
  throw new Error(`The manifest must grant host access to ${requiredOrigin}`);
}
for (const filename of runtimeFiles) {
  const filePath = path.join(sourceRoot, filename);
  if (!statSync(filePath).isFile()) {
    throw new Error(`Required extension file is missing: ${filename}`);
  }
}

const crcTable = new Uint32Array(256);
for (let index = 0; index < crcTable.length; index += 1) {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) {
    value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
  }
  crcTable[index] = value >>> 0;
}

function crc32(buffer) {
  let value = 0xffffffff;
  for (const byte of buffer) value = crcTable[(value ^ byte) & 0xff] ^ (value >>> 8);
  return (value ^ 0xffffffff) >>> 0;
}

function zipEntry(filename, content, offset) {
  const name = Buffer.from(filename, "utf8");
  const compressed = deflateRawSync(content, { level: 9 });
  const checksum = crc32(content);
  const local = Buffer.alloc(30);
  local.writeUInt32LE(0x04034b50, 0);
  local.writeUInt16LE(20, 4);
  local.writeUInt16LE(0x0800, 6);
  local.writeUInt16LE(8, 8);
  local.writeUInt32LE(checksum, 14);
  local.writeUInt32LE(compressed.length, 18);
  local.writeUInt32LE(content.length, 22);
  local.writeUInt16LE(name.length, 26);
  const localRecord = Buffer.concat([local, name, compressed]);

  const central = Buffer.alloc(46);
  central.writeUInt32LE(0x02014b50, 0);
  central.writeUInt16LE(20, 4);
  central.writeUInt16LE(20, 6);
  central.writeUInt16LE(0x0800, 8);
  central.writeUInt16LE(8, 10);
  central.writeUInt32LE(checksum, 16);
  central.writeUInt32LE(compressed.length, 20);
  central.writeUInt32LE(content.length, 24);
  central.writeUInt16LE(name.length, 28);
  central.writeUInt32LE(offset, 42);

  return { localRecord, centralRecord: Buffer.concat([central, name]) };
}

const localRecords = [];
const centralRecords = [];
let localOffset = 0;
for (const filename of runtimeFiles) {
  const content = readFileSync(path.join(sourceRoot, filename));
  const entry = zipEntry(filename, content, localOffset);
  localRecords.push(entry.localRecord);
  centralRecords.push(entry.centralRecord);
  localOffset += entry.localRecord.length;
}

const centralDirectory = Buffer.concat(centralRecords);
const end = Buffer.alloc(22);
end.writeUInt32LE(0x06054b50, 0);
end.writeUInt16LE(runtimeFiles.length, 8);
end.writeUInt16LE(runtimeFiles.length, 10);
end.writeUInt32LE(centralDirectory.length, 12);
end.writeUInt32LE(localOffset, 16);

const archive = Buffer.concat([...localRecords, centralDirectory, end]);
mkdirSync(path.dirname(outputPath), { recursive: true });
const temporaryPath = `${outputPath}.tmp`;
writeFileSync(temporaryPath, archive);
try {
  renameSync(temporaryPath, outputPath);
} catch (error) {
  if (!statSync(outputPath, { throwIfNoEntry: false })) throw error;
  const replacementPath = `${outputPath}.replacement`;
  copyFileSync(temporaryPath, replacementPath);
  rmSync(outputPath);
  renameSync(replacementPath, outputPath);
  rmSync(temporaryPath);
}

console.log(`Built ${path.relative(repoRoot, outputPath)} (${runtimeFiles.length} files).`);
