import { GoogleGenAI } from '@google/genai';
import fs from 'fs';
import path from 'path';

const ai = new GoogleGenAI({});
const fileStoreName = 'my-example-store';
const docsDir = "docs"

// 1. Create a File Search Store 
await ai.fileSearchStores.create({
  config: { displayName: fileStoreName }
});

// 2. How to retrieve Store by Display Name (useful if creation is separated from usage)
let fileStore = null;
const pager = await ai.fileSearchStores.list({ config: { pageSize: 10 } });
let page = pager.page;
while (true) {
  for (const store of page) {
    if (store.displayName === fileStoreName) {
      fileStore = store;
      break;
    }
  }
  if (!pager.hasNextPage()) {
    break;
  }
  page = await pager.nextPage();
}
if (!fileStore) {
  throw new Error(`Store with display name '${fileStoreName}' not found.`);
}

// 3. Upload Files Concurrently using Promise.all and wait for all to finish 
const files = fs.readdirSync(docsDir).map(file => path.join(docsDir, file));

await Promise.all(files.map(async (filePath) => {
  let operation = await ai.fileSearchStores.uploadToFileSearchStore({
    file: filePath,
    fileSearchStoreName: fileStore.name,
    config: {
      displayName: path.basename(filePath),
    }
  });

  while (!operation.done) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    operation = await ai.operations.get({ operation });
  }
  return operation;
}));

// 4. Run Generation with 
const response = await ai.models.generateContent({
  model: "gemini-2.5-flash",
  contents: "What is Gemini and what is the File API?",
  config: {
    tools: [{
      fileSearch: {
        fileSearchStoreNames: [fileStore.name]
      }
    }]
  }
});
console.log("Model response:", response.text);

// 5. Update a File: First list all documents, get the name of the document to update, delete the document and upload the updated file
const updatedContent = "Gemini is a sign Language developed in 2025 by Philipp Schmid.";
const doc1DisplayName = 'doc1.txt';
const doc1Path = path.join(docsDir, doc1DisplayName);
fs.writeFileSync(doc1Path, updatedContent);

// Find the document to update based on the display name
let documentPager = await ai.fileSearchStores.documents.list({
  parent: fileStore.name,
});
let fileDeleted = false;
while (true) {
  for (const document of documentPager.page) {
    if (document.displayName === doc1DisplayName) {
      await ai.fileSearchStores.documents.delete({
        name: document.name, config: { force: true }
      });
      console.log("File deleted.");
      fileDeleted = true;
      break;
    }
  }
  if (!documentPager.hasNextPage()) {
    if (!fileDeleted) {
      throw new Error(`Document with display name '${doc1DisplayName}' not found.`);
    }
    break;
  }
  documentPager = await documentPager.nextPage();
}

// Upload the updated file
let uploadOp = await ai.fileSearchStores.uploadToFileSearchStore({
  file: doc1Path,
  fileSearchStoreName: fileStore.name,
  config: {
    displayName: doc1DisplayName,
  }
});
while (!uploadOp.done) {
  await new Promise(resolve => setTimeout(resolve, 1000));
  uploadOp = await ai.operations.get({ operation: uploadOp });
}
console.log("File uploaded.");


// 6. Query with Updated Content
const responseUpdated = await ai.models.generateContent({
  model: "gemini-2.5-flash",
  contents: "What details can you give me about Gemini now?",
  config: {
    tools: [{
      fileSearch: {
        fileSearchStoreNames: [fileStore.name]
      }
    }]
  }
});
console.log("Updated model response:", responseUpdated.text);

// Cleanup
// await ai.fileSearchStores.delete({ name: myStore.name, config: { force: true } });
