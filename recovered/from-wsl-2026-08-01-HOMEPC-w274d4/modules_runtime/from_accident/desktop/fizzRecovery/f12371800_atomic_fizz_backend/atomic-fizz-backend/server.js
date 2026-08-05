const express = require('express');
const cors = require('cors');
const { Connection, Keypair, PublicKey, Transaction } = require('@solana/web3.js');
const { getOrCreateAssociatedTokenAccount, createMintToInstruction } = require('@solana/spl-token');

const app = express();
app.use(cors());
app.use(express.json());

const connection = new Connection('https://api.devnet.solana.com');
const MINT = new PublicKey('FywSJiYrtgErQwGeySiugRxCNg9xAnzRqmZQr6v2mEt2');
const AUTHORITY = Keypair.fromSecretKey(Uint8Array.from([103, 15, 177, 169, 209, 228, 118, 93, 8, 120, 130, 186, 86, 183, 118, 22, 169, 30, 202, 240, 33, 99, 59, 121, 148, 15, 4, 41, 55, 17, 86, 6, 73, 157, 113, 239, 163, 6, 214, 172, 75, 183, 117, 187, 208, 58, 97, 253, 66, 217, 229, 165, 144, 89, 146, 50, 195, 147, 193, 26, 225, 99, 219, 175]));

app.post('/mint-loot', async (req, res) => {
    const { wallet, spot } = req.body;
    try {
        const userPubkey = new PublicKey(wallet);
        const userATA = await getOrCreateAssociatedTokenAccount(connection, AUTHORITY, MINT, userPubkey);

        const tx = new Transaction().add(
            createMintToInstruction(MINT, userATA.address, AUTHORITY.publicKey, 25_000_000_000) // 25 CAPS
        );

        const { blockhash } = await connection.getLatestBlockhash();
        tx.recentBlockhash = blockhash;
        tx.feePayer = AUTHORITY.publicKey;
        tx.sign(AUTHORITY);

        const sig = await connection.sendRawTransaction(tx.serialize());
        await connection.confirmTransaction(sig);

        res.json({
            success: true,
            sig,
            explorer: `https://explorer.solana.com/tx/${sig}?cluster=devnet`,
            message: `+25 CAPS at ${spot}!`
        });
    } catch (e) {
        console.error(e);
        res.status(500).json({ error: e.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Atomic Fizz loot server LIVE on port ${PORT}`));