// This is a sample TypeScript file for testing the parser.

export class MyTsClass {
    constructor(public name: string) {}

    greet(): string {
        return `Hello, ${this.name}`;
    }
}

export function topLevelTsFunction(a: number, b: number): number {
    return a + b;
}
