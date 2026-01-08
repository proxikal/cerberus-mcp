// This is a sample JavaScript file for testing the parser.
import fs from "fs";

class MyJsClass {
    constructor(name) {
        this.name = name;
    }

    sayHello() {
        console.log(`Hello, ${this.name}`);
    }
}

function topLevelJsFunction(a, b) {
    fs.readFileSync("dummy.txt");
    return a * b;
}
